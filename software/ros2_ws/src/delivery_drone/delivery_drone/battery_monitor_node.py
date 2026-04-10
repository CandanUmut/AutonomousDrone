"""
Battery Monitor Node — tracks battery state and manages hot-swap station.

In simulation the battery state comes from the ArduPilot/MAVROS bridge.
On hardware it comes from a dedicated BMS or the flight controller.

Hot-swap logic
--------------
1. Drone lands at swap station (confirmed by LANDED state from mission manager).
2. Battery monitor detects battery percentage is below SWAP_THRESHOLD.
3. It publishes /drone/battery/swap_request = True.
4. An external station controller (Arduino Nano or similar) sees this and:
      - Releases the old battery (servo latch opens)
      - Waits for sensor confirmation that battery is removed
      - Slides in the new battery
      - Closes the latch
      - Publishes /drone/battery/swap_complete = True
5. Battery monitor sees swap_complete, reads the new voltage, and publishes
   /drone/battery/swap_ready = True when voltage confirms a good battery.
6. Mission manager transitions out of BATTERY_SWAP.

Topics (subscribe)
------------------
/mavros/battery              (sensor_msgs/BatteryState)
/drone/mission/state         (std_msgs/String)
/drone/battery/swap_complete (std_msgs/Bool)  — from station controller

Topics (publish)
----------------
/drone/battery/percentage    (std_msgs/Float32)  — 0–100
/drone/battery/voltage       (std_msgs/Float32)  — cell voltage avg
/drone/battery/swap_request  (std_msgs/Bool)
/drone/battery/swap_ready    (std_msgs/Bool)
/drone/battery/health        (std_msgs/String)   — OK / LOW / CRITICAL / UNKNOWN
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, Float32, String


class BatteryMonitorNode(Node):

    SWAP_THRESHOLD = 25.0       # % — request swap when below this after landing
    LOW_THRESHOLD = 30.0        # % — warn
    CRITICAL_THRESHOLD = 10.0   # % — emergency land (also handled in mission_manager)
    GOOD_CELL_VOLTAGE = 3.7     # V — minimum per-cell voltage for "good" battery
    CELLS = 6                   # 6S LiPo

    # Minimum voltage per cell to accept a freshly swapped battery
    MIN_FRESH_CELL_V = 3.9

    def __init__(self) -> None:
        super().__init__("battery_monitor_node")

        self.declare_parameter("swap_threshold_pct", self.SWAP_THRESHOLD)
        self.declare_parameter("cell_count", self.CELLS)
        self.declare_parameter("publish_rate_hz", 5.0)

        self._swap_threshold = self.get_parameter("swap_threshold_pct").value
        self._cells = self.get_parameter("cell_count").value

        self._percentage: float = 100.0
        self._voltage: float = 0.0
        self._current: float = 0.0
        self._mission_state: str = "IDLE"
        self._swap_complete: bool = False
        self._swap_requested: bool = False
        self._swap_ready_published: bool = False

        sensor_qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)

        # Subscribers
        self.create_subscription(
            BatteryState, "/mavros/battery", self._battery_cb, sensor_qos
        )
        self.create_subscription(
            String, "/drone/mission/state", self._mission_state_cb, 10
        )
        self.create_subscription(
            Bool, "/drone/battery/swap_complete", self._swap_complete_cb, 10
        )

        # Publishers
        self._pct_pub = self.create_publisher(Float32, "/drone/battery/percentage", 10)
        self._volt_pub = self.create_publisher(Float32, "/drone/battery/voltage", 10)
        self._swap_req_pub = self.create_publisher(Bool, "/drone/battery/swap_request", 10)
        self._swap_ready_pub = self.create_publisher(Bool, "/drone/battery/swap_ready", 10)
        self._health_pub = self.create_publisher(String, "/drone/battery/health", 10)

        rate = self.get_parameter("publish_rate_hz").value
        self.create_timer(1.0 / rate, self._publish_status)

        self.get_logger().info("Battery monitor started")

    # ------------------------------------------------------------------
    def _battery_cb(self, msg: BatteryState) -> None:
        # MAVROS BatteryState: percentage in [0, 1], voltage in V
        if msg.percentage >= 0:
            self._percentage = msg.percentage * 100.0
        self._voltage = msg.voltage
        if msg.current:
            self._current = msg.current

    def _mission_state_cb(self, msg: String) -> None:
        prev = self._mission_state
        self._mission_state = msg.data

        if prev != "LANDED" and self._mission_state == "LANDED":
            self._on_landed()

        if prev == "BATTERY_SWAP" and self._mission_state not in ("BATTERY_SWAP", "FAILED"):
            # Swap cycle ended (complete or failed) — reset flags
            self._swap_requested = False
            self._swap_ready_published = False

    def _swap_complete_cb(self, msg: Bool) -> None:
        self._swap_complete = msg.data
        if msg.data:
            self.get_logger().info("Station reports swap complete — verifying battery voltage")

    # ------------------------------------------------------------------
    def _on_landed(self) -> None:
        if self._percentage < self._swap_threshold:
            self.get_logger().info(
                f"Battery at {self._percentage:.0f}% — requesting swap"
            )
            self._swap_requested = True
        else:
            self.get_logger().info(
                f"Battery at {self._percentage:.0f}% — swap not needed"
            )

    # ------------------------------------------------------------------
    def _publish_status(self) -> None:
        now = self.get_clock().now().to_msg()

        pct_msg = Float32()
        pct_msg.data = self._percentage
        self._pct_pub.publish(pct_msg)

        volt_msg = Float32()
        volt_msg.data = self._voltage
        self._volt_pub.publish(volt_msg)

        # Health string
        health = self._health_string()
        health_msg = String()
        health_msg.data = health
        self._health_pub.publish(health_msg)

        if health in ("LOW", "CRITICAL"):
            self.get_logger().warning(
                f"Battery {health}: {self._percentage:.0f}%  {self._voltage:.2f} V"
            )

        # Swap request
        if self._swap_requested:
            req_msg = Bool()
            req_msg.data = True
            self._swap_req_pub.publish(req_msg)

        # Swap ready — check after swap_complete signal
        if self._swap_complete and not self._swap_ready_published:
            cell_v = self._voltage / self._cells if self._cells > 0 else 0.0
            ready = cell_v >= self.MIN_FRESH_CELL_V
            if ready:
                self.get_logger().info(
                    f"Fresh battery verified: {cell_v:.2f} V/cell — swap ready"
                )
            else:
                self.get_logger().warning(
                    f"Swapped battery low: {cell_v:.2f} V/cell (need ≥ {self.MIN_FRESH_CELL_V})"
                )
            ready_msg = Bool()
            ready_msg.data = ready
            self._swap_ready_pub.publish(ready_msg)
            self._swap_ready_published = True
            # Reset swap_complete for next cycle
            self._swap_complete = False

    def _health_string(self) -> str:
        if self._voltage == 0.0 and self._percentage == 100.0:
            return "UNKNOWN"  # No telemetry yet
        if self._percentage <= self.CRITICAL_THRESHOLD:
            return "CRITICAL"
        if self._percentage <= self.LOW_THRESHOLD:
            return "LOW"
        return "OK"


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = BatteryMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
