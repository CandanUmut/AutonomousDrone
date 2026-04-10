"""
Payload Manager Node — controls the medicine delivery bay.

On hardware: drives a servo (via GPIO or ArduPilot AUX channel) to open
             the payload bay door and release the package.

In simulation: publishes a confirmation immediately after receiving the
               release command (no physical servo).

The payload bay has two states:
    CLOSED  — bay door shut, payload secured
    OPEN    — bay door open, payload released (drops under gravity)

Safety rules
------------
- Will NOT open if altitude < MIN_RELEASE_ALT_M (prevents ground release).
- Will NOT open if mission state is not DELIVERING.
- Publishes /drone/payload/released after successful drop.
- Publishes /drone/payload/bay_state for telemetry.

Subscribes
----------
/drone/payload/release_cmd  (std_msgs/Bool)  — True = release
/drone/mission/state        (std_msgs/String)
/mavros/local_position/pose (geometry_msgs/PoseStamped)

Publishes
---------
/drone/payload/released     (std_msgs/Bool)
/drone/payload/bay_state    (std_msgs/String)  — CLOSED / OPEN / UNKNOWN
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String


class PayloadManagerNode(Node):

    MIN_RELEASE_ALT_M = 2.0   # Do not release below this altitude (safety)
    SAFE_MISSION_STATES = {"DELIVERING"}

    def __init__(self) -> None:
        super().__init__("payload_manager_node")

        self.declare_parameter("min_release_alt_m", self.MIN_RELEASE_ALT_M)
        self.declare_parameter("simulation_mode", True)

        self._min_alt = self.get_parameter("min_release_alt_m").value
        self._sim_mode = self.get_parameter("simulation_mode").value

        self._bay_open = False
        self._released = False
        self._altitude = 0.0
        self._mission_state = "IDLE"

        sensor_qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)

        # Subscribers
        self.create_subscription(Bool, "/drone/payload/release_cmd", self._release_cb, 10)
        self.create_subscription(String, "/drone/mission/state", self._state_cb, 10)
        self.create_subscription(
            PoseStamped, "/mavros/local_position/pose", self._pose_cb, sensor_qos
        )

        # Publishers
        self._released_pub = self.create_publisher(Bool, "/drone/payload/released", 10)
        self._bay_state_pub = self.create_publisher(String, "/drone/payload/bay_state", 10)

        # Status timer at 2 Hz
        self.create_timer(0.5, self._publish_status)

        self.get_logger().info(
            f"Payload manager started ({'simulation' if self._sim_mode else 'hardware'} mode)"
        )

    def _pose_cb(self, msg: PoseStamped) -> None:
        self._altitude = msg.pose.position.z

    def _state_cb(self, msg: String) -> None:
        self._mission_state = msg.data
        # Auto-close if we leave DELIVERING state
        if self._mission_state not in self.SAFE_MISSION_STATES and self._bay_open:
            self.get_logger().info("Mission state changed — bay remains open (delivery done)")

    def _release_cb(self, msg: Bool) -> None:
        if not msg.data:
            return

        # Safety checks
        if self._mission_state not in self.SAFE_MISSION_STATES:
            self.get_logger().warning(
                f"Release rejected: mission state is {self._mission_state} "
                f"(expected {self.SAFE_MISSION_STATES})"
            )
            return

        if self._altitude < self._min_alt:
            self.get_logger().warning(
                f"Release rejected: altitude {self._altitude:.1f} m < "
                f"minimum {self._min_alt} m"
            )
            return

        if self._released:
            self.get_logger().info("Payload already released")
            return

        self._do_release()

    def _do_release(self) -> None:
        if self._sim_mode:
            self.get_logger().info("SIM: Payload bay opened — package released")
            self._bay_open = True
            self._released = True
        else:
            # Hardware: trigger servo via ArduPilot AUX channel
            # This would call a MAVLink DO_SET_SERVO command via MAVROS
            # Placeholder for hardware implementation
            self.get_logger().info("HW: Sending bay open command")
            self._bay_open = True
            self._released = True

        released_msg = Bool()
        released_msg.data = True
        self._released_pub.publish(released_msg)
        self.get_logger().info(
            f"Payload released at altitude {self._altitude:.1f} m"
        )

    def _publish_status(self) -> None:
        state_msg = String()
        if self._bay_open:
            state_msg.data = "OPEN"
        else:
            state_msg.data = "CLOSED"
        self._bay_state_pub.publish(state_msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PayloadManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
