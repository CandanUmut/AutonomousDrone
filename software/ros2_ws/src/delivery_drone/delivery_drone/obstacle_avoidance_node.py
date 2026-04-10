"""
VFH+ (Vector Field Histogram Plus) Obstacle Avoidance Node

Algorithm:  Ulrich & Borenstein, "VFH+: Reliable Obstacle Avoidance for Fast
            Mobile Robots" (1998), adapted for aerial vehicle 2D LiDAR.

Subscribes:
    /scan                        (sensor_msgs/LaserScan)   — RPLidar 360° data
    /mavros/local_position/pose  (geometry_msgs/PoseStamped) — current pose
    /drone/goal_position         (geometry_msgs/PointStamped) — current waypoint

Publishes:
    /mavros/setpoint_velocity/cmd_vel_unstamped (geometry_msgs/Twist)
    /drone/vfh/histogram         (std_msgs/Float32MultiArray) — debug histogram
    /drone/vfh/chosen_direction  (std_msgs/Float32)           — debug direction

Parameters:
    alpha_deg          Polar sector width in degrees          (default: 5.0)
    threshold          Obstacle density threshold             (default: 0.6)
    safety_radius_m    Half-width of drone + margin (m)       (default: 0.6)
    max_speed_ms       Maximum forward speed (m/s)            (default: 2.0)
    max_range_m        Max LiDAR range used for avoidance (m) (default: 8.0)
    hysteresis_deg     Dead-band around current direction     (default: 10.0)
    cruise_altitude_m  Target altitude (m, for Z cmd)         (default: 15.0)
"""

from __future__ import annotations

import math

import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped, Twist
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32, Float32MultiArray


class VFHPlus:
    """
    Core VFH+ algorithm.  Operates in the robot's 2-D horizontal plane.
    All angles are measured from robot-forward (0°) increasing counter-clockwise.
    """

    def __init__(
        self,
        alpha_deg: float = 5.0,
        threshold: float = 0.6,
        safety_radius: float = 0.6,
        max_speed: float = 2.0,
        max_range: float = 8.0,
        hysteresis: float = 10.0,
    ) -> None:
        self.alpha = alpha_deg
        self.num_sectors = int(360 / alpha_deg)
        self.threshold = threshold
        self.safety_radius = safety_radius
        self.max_speed = max_speed
        self.max_range = max_range
        self.hysteresis = hysteresis

        # Smoothing window half-width (number of sectors each side)
        self._smooth_l = max(1, int(5.0 / alpha_deg))
        # Minimum sector count for a "wide" valley
        self._s_max = max(
            2,
            2 * math.ceil(safety_radius / (max_range * math.sin(math.radians(alpha_deg)))),
        )

        self._histogram: np.ndarray = np.zeros(self.num_sectors)
        self._prev_direction: float | None = None  # degrees, robot-frame

    # ------------------------------------------------------------------
    def build_histogram(
        self,
        ranges: list[float],
        angle_min_rad: float,
        angle_increment_rad: float,
    ) -> np.ndarray:
        """Build and smooth the polar obstacle density histogram."""
        raw = np.zeros(self.num_sectors)

        for i, d in enumerate(ranges):
            if not math.isfinite(d) or d <= 0.01 or d > self.max_range:
                continue
            angle_rad = angle_min_rad + i * angle_increment_rad
            # Normalise to [0, 360)
            angle_deg = math.degrees(angle_rad) % 360.0
            sector = int(angle_deg / self.alpha) % self.num_sectors

            # Certainty grows as obstacle is closer (quadratic)
            certainty = (1.0 - d / self.max_range) ** 2
            raw[sector] += certainty

        # Smooth with triangular window of width (2*l + 1)
        l = self._smooth_l
        smoothed = np.zeros(self.num_sectors)
        for k in range(self.num_sectors):
            total_weight = 0.0
            value = 0.0
            for j in range(-l, l + 1):
                w = l + 1 - abs(j)
                idx = (k + j) % self.num_sectors
                value += w * raw[idx]
                total_weight += w
            smoothed[k] = value / total_weight

        self._histogram = smoothed
        return smoothed

    # ------------------------------------------------------------------
    def _find_valleys(self, binary: np.ndarray) -> list[tuple[int, int]]:
        """
        Find contiguous free (True) sectors in the circular binary histogram.
        Returns list of (start_sector, end_sector) inclusive, handling wrap.
        """
        valleys: list[tuple[int, int]] = []
        n = self.num_sectors

        # Double the array to handle wrap-around
        doubled = np.tile(binary, 2)
        in_valley = False
        start = 0
        for i in range(2 * n):
            if doubled[i] and not in_valley:
                start = i
                in_valley = True
            elif not doubled[i] and in_valley:
                in_valley = False
                # Only record if contained within first n sectors
                if start < n:
                    end = (i - 1) % n
                    valleys.append((start % n, end))
        if in_valley and start < n:
            valleys.append((start % n, (2 * n - 1) % n))

        # Deduplicate
        seen: set[tuple[int, int]] = set()
        unique = []
        for v in valleys:
            if v not in seen:
                seen.add(v)
                unique.append(v)
        return unique

    # ------------------------------------------------------------------
    def _valley_size(self, start: int, end: int) -> int:
        n = self.num_sectors
        if end >= start:
            return end - start + 1
        return n - start + end + 1

    def _sector_distance(self, a: int, b: int) -> int:
        n = self.num_sectors
        d = abs(a - b)
        return min(d, n - d)

    # ------------------------------------------------------------------
    def select_direction(self, goal_angle_deg: float) -> float | None:
        """
        Select the best navigable direction (degrees, robot-frame).
        Returns None if completely blocked.
        """
        binary = self._histogram < self.threshold
        valleys = self._find_valleys(binary)

        if not valleys:
            return None  # Fully blocked — caller should stop/yaw

        goal_sector = int(goal_angle_deg / self.alpha) % self.num_sectors

        best_direction: float | None = None
        best_cost = float("inf")

        for v_start, v_end in valleys:
            v_size = self._valley_size(v_start, v_end)

            if v_size >= self._s_max:
                # Wide valley: steer toward goal if inside, else toward near edge
                in_valley = False
                for offset in range(v_size):
                    if (v_start + offset) % self.num_sectors == goal_sector:
                        in_valley = True
                        break

                if in_valley:
                    candidate = goal_sector
                else:
                    # Nearest edge (with safety margin)
                    margin = self._s_max // 2
                    dist_start = self._sector_distance(goal_sector, v_start)
                    dist_end = self._sector_distance(goal_sector, v_end)
                    if dist_start <= dist_end:
                        candidate = (v_start + margin) % self.num_sectors
                    else:
                        candidate = (v_end - margin) % self.num_sectors
            else:
                # Narrow valley: aim at centre
                candidate = (v_start + v_size // 2) % self.num_sectors

            # Cost = alignment with goal + hysteresis penalty for large turns
            delta_goal = self._sector_distance(candidate, goal_sector)
            hysteresis_penalty = 0.0
            if self._prev_direction is not None:
                prev_sector = int(self._prev_direction / self.alpha) % self.num_sectors
                delta_prev = self._sector_distance(candidate, prev_sector)
                hysteresis_penalty = (
                    0.3 * delta_prev if delta_prev * self.alpha > self.hysteresis else 0.0
                )

            cost = delta_goal + hysteresis_penalty
            if cost < best_cost:
                best_cost = cost
                best_direction = (candidate * self.alpha + self.alpha / 2.0) % 360.0

        self._prev_direction = best_direction
        return best_direction

    # ------------------------------------------------------------------
    def compute_velocity(
        self,
        goal_angle_robot_frame_deg: float,
        goal_distance_m: float,
    ) -> tuple[float, float]:
        """
        Returns (forward_speed_ms, yaw_rate_rads).
        goal_angle_robot_frame_deg: angle TO goal measured from robot forward,
                                    CCW positive, range [-180, 180].
        """
        # Normalise goal angle to [0, 360)
        goal_norm = goal_angle_robot_frame_deg % 360.0
        chosen = self.select_direction(goal_norm)

        if chosen is None:
            # Blocked: stop and rotate slowly
            return 0.0, 0.3

        # Convert chosen sector back to signed angle from forward
        # Forward = 0°, so error = chosen - 0° (= chosen, normalised to [-180, 180])
        heading_error_deg = chosen if chosen <= 180.0 else chosen - 360.0
        heading_error_rad = math.radians(heading_error_deg)

        # Slow down when turning sharply
        alignment = math.cos(heading_error_rad)
        forward_speed = self.max_speed * max(0.0, alignment)

        # Slow down when approaching goal
        if goal_distance_m < 5.0:
            forward_speed *= goal_distance_m / 5.0

        forward_speed = min(forward_speed, self.max_speed)

        # Proportional yaw rate
        yaw_rate = float(np.clip(-heading_error_rad * 0.8, -1.2, 1.2))

        return forward_speed, yaw_rate

    @property
    def histogram(self) -> np.ndarray:
        return self._histogram.copy()


# ======================================================================
class ObstacleAvoidanceNode(Node):

    def __init__(self) -> None:
        super().__init__("obstacle_avoidance_node")

        # Parameters
        self.declare_parameter("alpha_deg", 5.0)
        self.declare_parameter("threshold", 0.6)
        self.declare_parameter("safety_radius_m", 0.6)
        self.declare_parameter("max_speed_ms", 2.0)
        self.declare_parameter("max_range_m", 8.0)
        self.declare_parameter("hysteresis_deg", 10.0)
        self.declare_parameter("cruise_altitude_m", 15.0)
        self.declare_parameter("goal_reached_radius_m", 2.0)

        self._vfh = VFHPlus(
            alpha_deg=self.get_parameter("alpha_deg").value,
            threshold=self.get_parameter("threshold").value,
            safety_radius=self.get_parameter("safety_radius_m").value,
            max_speed=self.get_parameter("max_speed_ms").value,
            max_range=self.get_parameter("max_range_m").value,
            hysteresis=self.get_parameter("hysteresis_deg").value,
        )
        self._cruise_alt = self.get_parameter("cruise_altitude_m").value
        self._goal_radius = self.get_parameter("goal_reached_radius_m").value

        self._current_pose: PoseStamped | None = None
        self._goal: PointStamped | None = None
        self._active = False  # Only publish velocity when active

        # QoS for MAVROS
        sensor_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        # Subscribers
        self.create_subscription(LaserScan, "/scan", self._scan_cb, sensor_qos)
        self.create_subscription(
            PoseStamped, "/mavros/local_position/pose", self._pose_cb, sensor_qos
        )
        self.create_subscription(
            PointStamped, "/drone/goal_position", self._goal_cb, 10
        )

        # Publishers
        self._cmd_pub = self.create_publisher(Twist, "/mavros/setpoint_velocity/cmd_vel_unstamped", 10)
        self._hist_pub = self.create_publisher(Float32MultiArray, "/drone/vfh/histogram", 10)
        self._dir_pub = self.create_publisher(Float32, "/drone/vfh/chosen_direction", 10)

        # 10 Hz control loop (aligns with LiDAR update rate)
        self.create_timer(0.1, self._control_loop)

        self.get_logger().info("VFH+ obstacle avoidance node started")

    # ------------------------------------------------------------------
    def _scan_cb(self, msg: LaserScan) -> None:
        self._vfh.build_histogram(
            list(msg.ranges), msg.angle_min, msg.angle_increment
        )

        # Publish debug histogram
        hist_msg = Float32MultiArray()
        hist_msg.data = self._vfh.histogram.tolist()
        self._hist_pub.publish(hist_msg)

    def _pose_cb(self, msg: PoseStamped) -> None:
        self._current_pose = msg

    def _goal_cb(self, msg: PointStamped) -> None:
        self._goal = msg
        self._active = True
        self.get_logger().info(
            f"New goal: ({msg.point.x:.1f}, {msg.point.y:.1f}, {msg.point.z:.1f})"
        )

    # ------------------------------------------------------------------
    def _control_loop(self) -> None:
        if not self._active or self._current_pose is None or self._goal is None:
            return

        pos = self._current_pose.pose.position
        goal = self._goal.point

        # Horizontal distance to goal
        dx = goal.x - pos.x
        dy = goal.y - pos.y
        dist = math.sqrt(dx**2 + dy**2)

        if dist < self._goal_radius:
            # Goal reached — stop horizontal motion
            cmd = Twist()
            self.get_logger().info("Goal reached")
            self._active = False
            self._cmd_pub.publish(cmd)
            return

        # Goal angle in world frame (0° = East/+X)
        goal_angle_world = math.degrees(math.atan2(dy, dx))

        # Get drone yaw from quaternion
        q = self._current_pose.pose.orientation
        yaw_rad = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y**2 + q.z**2),
        )
        drone_yaw_deg = math.degrees(yaw_rad)

        # Goal angle in robot frame
        goal_angle_robot = (goal_angle_world - drone_yaw_deg) % 360.0

        # VFH+ output
        fwd_speed, yaw_rate = self._vfh.compute_velocity(goal_angle_robot, dist)

        # Altitude correction (simple P-controller)
        alt_error = self._cruise_alt - pos.z
        vz = float(np.clip(alt_error * 0.5, -1.0, 1.0))

        # Build Twist in body frame: x=forward, z=up, angular.z=yaw
        cmd = Twist()
        cmd.linear.x = fwd_speed
        cmd.linear.z = vz
        cmd.angular.z = yaw_rate
        self._cmd_pub.publish(cmd)

        # Publish chosen direction for debug
        chosen = self._vfh.select_direction(goal_angle_robot)
        if chosen is not None:
            dir_msg = Float32()
            dir_msg.data = float(chosen)
            self._dir_pub.publish(dir_msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ObstacleAvoidanceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
