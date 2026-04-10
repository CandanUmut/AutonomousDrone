"""
Precision Landing Node — ArUco marker detection for pad alignment.

Uses the downward-facing camera to detect ArUco marker ID 0 (DICT_4X4_50)
on the landing pad and publishes velocity corrections so the drone centres
over the marker before touchdown.

Algorithm
---------
1. Detect marker corners in downward camera image.
2. Estimate 3-D pose of marker relative to camera (solvePnP).
3. Compute (x_err, y_err) — lateral offset of drone centre from marker centre.
4. Publish a corrective velocity command (body frame) proportional to error
   (P-controller). The mission manager handles descent rate.
5. When the drone is within dead-band (< 0.1 m) and altitude < 2 m,
   publish /drone/precision_landing/aligned so the mission manager knows
   it can command final touchdown.

Subscribes
----------
/camera/down/image_raw    (sensor_msgs/Image)
/camera/down/camera_info  (sensor_msgs/CameraInfo)
/drone/precision_landing/enable (std_msgs/Bool) — enable gate
/mavros/local_position/pose (geometry_msgs/PoseStamped)

Publishes
---------
/drone/precision_landing/detected (std_msgs/Bool)
/drone/precision_landing/aligned  (std_msgs/Bool)
/drone/precision_landing/offset   (geometry_msgs/Vector3Stamped)
/mavros/setpoint_velocity/cmd_vel_unstamped (geometry_msgs/Twist) — lateral corrections
"""

from __future__ import annotations

import math

import cv2
import cv2.aruco as aruco
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped, Twist, Vector3Stamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool


class PrecisionLandingNode(Node):

    MARKER_DICT = aruco.DICT_4X4_50
    ALIGN_DEADBAND_M = 0.10   # metres — centred if error < this
    ALIGN_ALT_M = 2.5         # metres — publish aligned only below this
    MAX_LATERAL_SPEED = 0.5   # m/s
    DESCENT_RATE = -0.3       # m/s (negative = downward in ENU)
    KP = 0.6                  # Proportional gain for lateral corrections

    def __init__(self) -> None:
        super().__init__("precision_landing_node")

        self.declare_parameter("marker_id", 0)
        self.declare_parameter("marker_size_m", 0.5)
        self.declare_parameter("camera_frame_offset_x", 0.0)  # camera offset from CG (m)
        self.declare_parameter("camera_frame_offset_y", 0.0)

        self._marker_id: int = self.get_parameter("marker_id").value
        self._marker_size: float = self.get_parameter("marker_size_m").value
        self._cam_offset_x: float = self.get_parameter("camera_frame_offset_x").value
        self._cam_offset_y: float = self.get_parameter("camera_frame_offset_y").value

        # ArUco detector
        aruco_dict = aruco.getPredefinedDictionary(self.MARKER_DICT)
        aruco_params = aruco.DetectorParameters()
        self._detector = aruco.ArucoDetector(aruco_dict, aruco_params)

        self._bridge = CvBridge()
        self._camera_matrix: np.ndarray | None = None
        self._dist_coeffs: np.ndarray | None = None
        self._enabled = False
        self._altitude = float("inf")

        sensor_qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)

        # Subscribers
        self.create_subscription(Image, "/camera/down/image_raw", self._image_cb, sensor_qos)
        self.create_subscription(
            CameraInfo, "/camera/down/camera_info", self._camera_info_cb, 10
        )
        self.create_subscription(Bool, "/drone/precision_landing/enable", self._enable_cb, 10)
        self.create_subscription(
            PoseStamped, "/mavros/local_position/pose", self._pose_cb, sensor_qos
        )

        # Publishers
        self._detected_pub = self.create_publisher(Bool, "/drone/precision_landing/detected", 10)
        self._aligned_pub = self.create_publisher(Bool, "/drone/precision_landing/aligned", 10)
        self._offset_pub = self.create_publisher(
            Vector3Stamped, "/drone/precision_landing/offset", 10
        )
        self._cmd_pub = self.create_publisher(
            Twist, "/mavros/setpoint_velocity/cmd_vel_unstamped", 10
        )

        self.get_logger().info(
            f"Precision landing node started (marker ID {self._marker_id}, "
            f"size {self._marker_size} m)"
        )

    # ------------------------------------------------------------------
    def _enable_cb(self, msg: Bool) -> None:
        self._enabled = msg.data
        if self._enabled:
            self.get_logger().info("Precision landing enabled")
        else:
            self.get_logger().info("Precision landing disabled")

    def _pose_cb(self, msg: PoseStamped) -> None:
        self._altitude = msg.pose.position.z

    def _camera_info_cb(self, msg: CameraInfo) -> None:
        if self._camera_matrix is None:
            self._camera_matrix = np.array(msg.k).reshape(3, 3)
            self._dist_coeffs = np.array(msg.d)
            self.get_logger().info("Camera calibration received")

    def _image_cb(self, msg: Image) -> None:
        if not self._enabled or self._camera_matrix is None:
            return
        try:
            self._process_image(msg)
        except Exception as exc:
            self.get_logger().error(f"Image processing error: {exc}")

    # ------------------------------------------------------------------
    def _process_image(self, msg: Image) -> None:
        cv_image = self._bridge.imgmsg_to_cv2(msg, "bgr8")
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        corners, ids, _ = self._detector.detectMarkers(gray)

        detected_msg = Bool()
        aligned_msg = Bool()

        if ids is None or self._marker_id not in ids.flatten():
            detected_msg.data = False
            aligned_msg.data = False
            self._detected_pub.publish(detected_msg)
            self._aligned_pub.publish(aligned_msg)
            return

        # Find our target marker
        idx = int(np.where(ids.flatten() == self._marker_id)[0][0])
        target_corners = corners[idx]

        # Estimate pose — rvec/tvec give camera-to-marker transform
        rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
            target_corners, self._marker_size, self._camera_matrix, self._dist_coeffs
        )
        # tvec[0][0]: [x, y, z] in camera frame
        # For downward camera (optical axis = -Z body):
        #   tvec.x  = rightward offset of marker from camera (body +Y)
        #   tvec.y  = forward offset of marker from camera (body +X)  [note: image Y is flipped]
        #   tvec.z  = height above marker (body +Z = up)
        tx = float(tvec[0][0][0])  # lateral (image X → body Y)
        ty = float(tvec[0][0][1])  # longitudinal (image Y → body X, negated)
        tz = float(tvec[0][0][2])  # distance from camera to marker

        # Account for camera offset from CG
        # Offset: if camera is 5 cm ahead of CG, marker appears 5 cm behind
        body_x_err = -ty - self._cam_offset_x  # forward error
        body_y_err = tx - self._cam_offset_y   # lateral error
        horizontal_err = math.sqrt(body_x_err**2 + body_y_err**2)

        # Publish offset
        offset_msg = Vector3Stamped()
        offset_msg.header = msg.header
        offset_msg.vector.x = body_x_err
        offset_msg.vector.y = body_y_err
        offset_msg.vector.z = tz
        self._offset_pub.publish(offset_msg)

        detected_msg.data = True
        self._detected_pub.publish(detected_msg)

        # Compute lateral correction velocity (P-controller, body frame)
        vx = float(np.clip(self.KP * body_x_err, -self.MAX_LATERAL_SPEED, self.MAX_LATERAL_SPEED))
        vy = float(np.clip(self.KP * body_y_err, -self.MAX_LATERAL_SPEED, self.MAX_LATERAL_SPEED))

        # Only descend when reasonably centred
        centred = horizontal_err < self.ALIGN_DEADBAND_M * 3.0
        vz = self.DESCENT_RATE if centred else 0.0

        cmd = Twist()
        cmd.linear.x = vx
        cmd.linear.y = vy
        cmd.linear.z = vz
        self._cmd_pub.publish(cmd)

        # Publish aligned when within deadband at low altitude
        is_aligned = (
            horizontal_err < self.ALIGN_DEADBAND_M
            and self._altitude < self.ALIGN_ALT_M
        )
        aligned_msg.data = is_aligned
        self._aligned_pub.publish(aligned_msg)

        if is_aligned:
            self.get_logger().debug(
                f"Aligned: err=({body_x_err:.3f}, {body_y_err:.3f}) m, "
                f"alt={self._altitude:.2f} m"
            )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PrecisionLandingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
