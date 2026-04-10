"""
Mission Manager Node — delivery state machine.

States
------
IDLE              Waiting for a mission command
PREFLIGHT         Running preflight checks (GPS lock, battery, arming)
ARMING            Sending arm command via MAVROS
TAKEOFF           Climbing to cruise altitude
NAVIGATING        Flying toward delivery waypoint (VFH+ active)
APPROACHING       Within 20 m of delivery point; slowing down
DELIVERING        Hovering; waiting for payload release confirmation
ASCENDING         Climbing back to cruise alt after delivery
RETURNING         Flying back toward home / swap station
APPROACH_STATION  Within 30 m of home; starting precision approach
PRECISION_LANDING ArUco-guided descent to swap station pad
LANDED            On ground; waiting for battery swap or mission end
BATTERY_SWAP      Battery swap in progress
EMERGENCY_RTL     Low battery — return immediately
EMERGENCY_LAND    Critical — land in place
COMPLETE          Mission finished successfully
FAILED            Unrecoverable error

Subscribes
----------
/mavros/state               (mavros_msgs/State)
/mavros/local_position/pose (geometry_msgs/PoseStamped)
/drone/battery/percentage   (std_msgs/Float32)
/drone/battery/swap_ready   (std_msgs/Bool)  — from battery_monitor
/drone/precision_landing/detected (std_msgs/Bool)
/drone/payload/released     (std_msgs/Bool)

Publishes
---------
/drone/mission/state        (std_msgs/String) — current state name
/drone/goal_position        (geometry_msgs/PointStamped) — for VFH+
/drone/precision_landing/enable (std_msgs/Bool)
/drone/payload/release_cmd  (std_msgs/Bool)
/mavros/cmd/arming          (via service)
/mavros/set_mode            (via service)
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from typing import Any

import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, SetMode
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, Float32, String


class MissionState(enum.StrEnum):
    IDLE = "IDLE"
    PREFLIGHT = "PREFLIGHT"
    ARMING = "ARMING"
    TAKEOFF = "TAKEOFF"
    NAVIGATING = "NAVIGATING"
    APPROACHING = "APPROACHING"
    DELIVERING = "DELIVERING"
    ASCENDING = "ASCENDING"
    RETURNING = "RETURNING"
    APPROACH_STATION = "APPROACH_STATION"
    PRECISION_LANDING = "PRECISION_LANDING"
    LANDED = "LANDED"
    BATTERY_SWAP = "BATTERY_SWAP"
    EMERGENCY_RTL = "EMERGENCY_RTL"
    EMERGENCY_LAND = "EMERGENCY_LAND"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class Waypoint:
    x: float  # Local ENU metres
    y: float
    z: float
    name: str = ""


class MissionManagerNode(Node):

    # Battery thresholds
    BATT_LOW = 25.0       # % — trigger RTL if not already returning
    BATT_CRITICAL = 10.0  # % — emergency land in place

    # Distance thresholds (metres)
    GOAL_REACHED_M = 3.0
    APPROACH_RADIUS_M = 20.0
    STATION_APPROACH_M = 30.0
    ARUCO_ENABLE_ALT_M = 10.0  # Enable ArUco detection below this altitude

    # Altitudes
    CRUISE_ALT_M = 15.0
    DELIVER_ALT_M = 5.0
    LAND_DESCENT_M = 0.3  # Target altitude above pad during precision landing

    def __init__(self) -> None:
        super().__init__("mission_manager_node")

        # Parameters
        self.declare_parameter("home_x", 0.0)
        self.declare_parameter("home_y", 0.0)
        self.declare_parameter("delivery_x", 80.0)
        self.declare_parameter("delivery_y", 5.0)
        self.declare_parameter("cruise_alt_m", self.CRUISE_ALT_M)
        self.declare_parameter("deliver_alt_m", self.DELIVER_ALT_M)
        self.declare_parameter("preflight_timeout_s", 30.0)
        self.declare_parameter("arm_timeout_s", 10.0)
        self.declare_parameter("takeoff_timeout_s", 30.0)
        self.declare_parameter("delivery_hover_s", 5.0)
        self.declare_parameter("swap_timeout_s", 300.0)

        self._home = Waypoint(
            x=self.get_parameter("home_x").value,
            y=self.get_parameter("home_y").value,
            z=0.0,
            name="home",
        )
        self._delivery = Waypoint(
            x=self.get_parameter("delivery_x").value,
            y=self.get_parameter("delivery_y").value,
            z=self.get_parameter("deliver_alt_m").value,
            name="delivery",
        )
        self._cruise_alt = self.get_parameter("cruise_alt_m").value
        self._delivery_hover_s = self.get_parameter("delivery_hover_s").value
        self._swap_timeout_s = self.get_parameter("swap_timeout_s").value

        # State
        self._state = MissionState.IDLE
        self._prev_state = MissionState.IDLE
        self._pose: PoseStamped | None = None
        self._mav_state: State | None = None
        self._battery_pct: float = 100.0
        self._swap_ready = False
        self._aruco_detected = False
        self._payload_released = False
        self._state_entry_time: float = 0.0
        self._delivering_start: float | None = None
        self._swap_start: float | None = None

        # QoS
        sensor_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        # Subscribers
        self.create_subscription(State, "/mavros/state", self._mav_state_cb, sensor_qos)
        self.create_subscription(
            PoseStamped, "/mavros/local_position/pose", self._pose_cb, sensor_qos
        )
        self.create_subscription(Float32, "/drone/battery/percentage", self._batt_cb, 10)
        self.create_subscription(Bool, "/drone/battery/swap_ready", self._swap_ready_cb, 10)
        self.create_subscription(
            Bool, "/drone/precision_landing/detected", self._aruco_cb, 10
        )
        self.create_subscription(Bool, "/drone/payload/released", self._payload_cb, 10)

        # Publishers
        self._state_pub = self.create_publisher(String, "/drone/mission/state", 10)
        self._goal_pub = self.create_publisher(PointStamped, "/drone/goal_position", 10)
        self._aruco_enable_pub = self.create_publisher(Bool, "/drone/precision_landing/enable", 10)
        self._payload_cmd_pub = self.create_publisher(Bool, "/drone/payload/release_cmd", 10)

        # MAVROS services
        self._arming_client = self.create_client(CommandBool, "/mavros/cmd/arming")
        self._mode_client = self.create_client(SetMode, "/mavros/set_mode")

        # 5 Hz state machine tick
        self.create_timer(0.2, self._tick)

        self.get_logger().info("Mission manager started — state: IDLE")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _mav_state_cb(self, msg: State) -> None:
        self._mav_state = msg

    def _pose_cb(self, msg: PoseStamped) -> None:
        self._pose = msg

    def _batt_cb(self, msg: Float32) -> None:
        self._battery_pct = msg.data
        # Interrupt for critical battery regardless of state
        if self._battery_pct <= self.BATT_CRITICAL and self._state not in (
            MissionState.EMERGENCY_LAND,
            MissionState.LANDED,
            MissionState.COMPLETE,
            MissionState.FAILED,
        ):
            self.get_logger().error(
                f"CRITICAL battery {self._battery_pct:.0f}% — emergency landing"
            )
            self._transition(MissionState.EMERGENCY_LAND)

    def _swap_ready_cb(self, msg: Bool) -> None:
        self._swap_ready = msg.data

    def _aruco_cb(self, msg: Bool) -> None:
        self._aruco_detected = msg.data

    def _payload_cb(self, msg: Bool) -> None:
        self._payload_released = msg.data

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _transition(self, new_state: MissionState) -> None:
        if new_state == self._state:
            return
        self.get_logger().info(f"State: {self._state} → {new_state}")
        self._prev_state = self._state
        self._state = new_state
        self._state_entry_time = self.get_clock().now().nanoseconds * 1e-9

        state_msg = String()
        state_msg.data = new_state.value
        self._state_pub.publish(state_msg)

    def _elapsed(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9 - self._state_entry_time

    def _dist_xy(self, x: float, y: float) -> float:
        if self._pose is None:
            return float("inf")
        p = self._pose.pose.position
        return math.sqrt((p.x - x) ** 2 + (p.y - y) ** 2)

    def _altitude(self) -> float:
        if self._pose is None:
            return 0.0
        return self._pose.pose.position.z

    def _publish_goal(self, x: float, y: float, z: float) -> None:
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.point.x = x
        msg.point.y = y
        msg.point.z = z
        self._goal_pub.publish(msg)

    def _set_aruco_enabled(self, enabled: bool) -> None:
        msg = Bool()
        msg.data = enabled
        self._aruco_enable_pub.publish(msg)

    def _call_arm(self, arm: bool) -> None:
        if not self._arming_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warning("Arming service not available")
            return
        req = CommandBool.Request()
        req.value = arm
        self._arming_client.call_async(req)

    def _set_mode(self, mode: str) -> None:
        if not self._mode_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warning("Set mode service not available")
            return
        req = SetMode.Request()
        req.custom_mode = mode
        self._mode_client.call_async(req)

    def _low_battery_interrupt(self) -> bool:
        """Return True if a low-battery RTL was triggered (state changed)."""
        if self._battery_pct <= self.BATT_LOW and self._state not in (
            MissionState.RETURNING,
            MissionState.APPROACH_STATION,
            MissionState.PRECISION_LANDING,
            MissionState.LANDED,
            MissionState.BATTERY_SWAP,
            MissionState.EMERGENCY_RTL,
            MissionState.EMERGENCY_LAND,
            MissionState.COMPLETE,
            MissionState.FAILED,
            MissionState.IDLE,
        ):
            self.get_logger().warning(
                f"Low battery {self._battery_pct:.0f}% — initiating emergency RTL"
            )
            self._transition(MissionState.EMERGENCY_RTL)
            return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_mission(self) -> None:
        if self._state != MissionState.IDLE:
            self.get_logger().warning(
                f"start_mission ignored — current state: {self._state}"
            )
            return
        self._payload_released = False
        self._transition(MissionState.PREFLIGHT)

    # ------------------------------------------------------------------
    # State machine tick (5 Hz)
    # ------------------------------------------------------------------
    def _tick(self) -> None:  # noqa: C901 (intentionally large switch)
        state = self._state

        if state == MissionState.IDLE:
            pass  # Wait for start_mission() call

        elif state == MissionState.PREFLIGHT:
            self._tick_preflight()

        elif state == MissionState.ARMING:
            self._tick_arming()

        elif state == MissionState.TAKEOFF:
            self._tick_takeoff()

        elif state == MissionState.NAVIGATING:
            if self._low_battery_interrupt():
                return
            self._tick_navigating()

        elif state == MissionState.APPROACHING:
            if self._low_battery_interrupt():
                return
            self._tick_approaching()

        elif state == MissionState.DELIVERING:
            if self._low_battery_interrupt():
                return
            self._tick_delivering()

        elif state == MissionState.ASCENDING:
            self._tick_ascending()

        elif state == MissionState.RETURNING:
            if self._low_battery_interrupt():
                return
            self._tick_returning()

        elif state == MissionState.APPROACH_STATION:
            self._tick_approach_station()

        elif state == MissionState.PRECISION_LANDING:
            self._tick_precision_landing()

        elif state == MissionState.LANDED:
            self._tick_landed()

        elif state == MissionState.BATTERY_SWAP:
            self._tick_battery_swap()

        elif state == MissionState.EMERGENCY_RTL:
            self._tick_emergency_rtl()

        elif state == MissionState.EMERGENCY_LAND:
            self._set_mode("AUTO.LAND")

        elif state in (MissionState.COMPLETE, MissionState.FAILED):
            pass  # Terminal states

    # ------------------------------------------------------------------
    # Individual state handlers
    # ------------------------------------------------------------------
    def _tick_preflight(self) -> None:
        timeout = self.get_parameter("preflight_timeout_s").value
        if self._mav_state is None:
            if self._elapsed() > timeout:
                self.get_logger().error("Preflight timeout: no MAVROS connection")
                self._transition(MissionState.FAILED)
            return

        gps_ok = True  # Simplified; real check: /mavros/global_position/fix
        batt_ok = self._battery_pct > 30.0
        fc_connected = self._mav_state.connected

        if fc_connected and gps_ok and batt_ok:
            self.get_logger().info("Preflight checks passed")
            self._transition(MissionState.ARMING)
        elif self._elapsed() > timeout:
            self.get_logger().error(
                f"Preflight timeout (connected={fc_connected}, batt={self._battery_pct:.0f}%)"
            )
            self._transition(MissionState.FAILED)

    def _tick_arming(self) -> None:
        timeout = self.get_parameter("arm_timeout_s").value
        if self._mav_state and self._mav_state.armed:
            self.get_logger().info("Armed — switching to GUIDED for takeoff")
            self._set_mode("GUIDED")
            self._transition(MissionState.TAKEOFF)
            return
        # Re-send arm command every 2 s
        if int(self._elapsed() * 2) % 4 == 0:
            self._call_arm(True)
        if self._elapsed() > timeout:
            self.get_logger().error("Arm timeout")
            self._transition(MissionState.FAILED)

    def _tick_takeoff(self) -> None:
        timeout = self.get_parameter("takeoff_timeout_s").value
        target_alt = self._cruise_alt
        self._publish_goal(
            self._pose.pose.position.x if self._pose else 0.0,
            self._pose.pose.position.y if self._pose else 0.0,
            target_alt,
        )
        if self._altitude() >= target_alt * 0.9:
            self.get_logger().info(f"Reached cruise altitude {self._altitude():.1f} m")
            self._transition(MissionState.NAVIGATING)
        elif self._elapsed() > timeout:
            self.get_logger().error("Takeoff timeout")
            self._transition(MissionState.FAILED)

    def _tick_navigating(self) -> None:
        dist = self._dist_xy(self._delivery.x, self._delivery.y)
        self._publish_goal(self._delivery.x, self._delivery.y, self._cruise_alt)
        if dist < self.APPROACH_RADIUS_M:
            self.get_logger().info(f"Approaching delivery point ({dist:.1f} m)")
            self._transition(MissionState.APPROACHING)

    def _tick_approaching(self) -> None:
        dist = self._dist_xy(self._delivery.x, self._delivery.y)
        self._publish_goal(self._delivery.x, self._delivery.y, self._delivery.z)
        if dist < self.GOAL_REACHED_M and abs(self._altitude() - self._delivery.z) < 1.0:
            self.get_logger().info("At delivery point — releasing payload")
            self._transition(MissionState.DELIVERING)

    def _tick_delivering(self) -> None:
        if self._delivering_start is None:
            self._delivering_start = self.get_clock().now().nanoseconds * 1e-9
            release_cmd = Bool()
            release_cmd.data = True
            self._payload_cmd_pub.publish(release_cmd)

        elapsed = self.get_clock().now().nanoseconds * 1e-9 - self._delivering_start
        if self._payload_released or elapsed > self._delivery_hover_s:
            if not self._payload_released:
                self.get_logger().warning("Payload release not confirmed; continuing anyway")
            self._delivering_start = None
            self._transition(MissionState.ASCENDING)

    def _tick_ascending(self) -> None:
        self._publish_goal(
            self._delivery.x, self._delivery.y, self._cruise_alt
        )
        if self._altitude() >= self._cruise_alt * 0.9:
            self._transition(MissionState.RETURNING)

    def _tick_returning(self) -> None:
        dist = self._dist_xy(self._home.x, self._home.y)
        self._publish_goal(self._home.x, self._home.y, self._cruise_alt)
        if dist < self.STATION_APPROACH_M:
            self.get_logger().info("Station in range — switching to precision approach")
            self._transition(MissionState.APPROACH_STATION)

    def _tick_approach_station(self) -> None:
        dist = self._dist_xy(self._home.x, self._home.y)
        # Descend to enable ArUco detection at lower altitude
        target_z = max(self._cruise_alt * 0.5, self.ARUCO_ENABLE_ALT_M)
        self._publish_goal(self._home.x, self._home.y, target_z)
        self._set_aruco_enabled(True)

        if dist < self.GOAL_REACHED_M:
            self._transition(MissionState.PRECISION_LANDING)

    def _tick_precision_landing(self) -> None:
        # ArUco node controls lateral corrections; we command descent
        if self._altitude() <= 0.5:
            self.get_logger().info("Touched down")
            self._set_aruco_enabled(False)
            self._call_arm(False)  # Disarm
            self._transition(MissionState.LANDED)
        else:
            # Let precision_landing_node publish velocity corrections;
            # we just set a gentle descent goal
            pos = self._pose.pose.position if self._pose else None
            if pos:
                self._publish_goal(pos.x, pos.y, 0.0)

    def _tick_landed(self) -> None:
        if self._battery_pct < self.BATT_LOW:
            self.get_logger().info("Initiating battery swap")
            self._swap_start = self.get_clock().now().nanoseconds * 1e-9
            self._transition(MissionState.BATTERY_SWAP)
        else:
            self.get_logger().info("Battery sufficient — mission complete")
            self._transition(MissionState.COMPLETE)

    def _tick_battery_swap(self) -> None:
        elapsed = self.get_clock().now().nanoseconds * 1e-9 - (self._swap_start or 0.0)
        if self._swap_ready:
            self.get_logger().info("Battery swap complete — ready for next mission")
            self._swap_start = None
            self._transition(MissionState.COMPLETE)
        elif elapsed > self._swap_timeout_s:
            self.get_logger().error("Battery swap timeout — mission failed")
            self._transition(MissionState.FAILED)

    def _tick_emergency_rtl(self) -> None:
        dist = self._dist_xy(self._home.x, self._home.y)
        self._publish_goal(self._home.x, self._home.y, self._cruise_alt)
        if dist < self.STATION_APPROACH_M:
            self._transition(MissionState.APPROACH_STATION)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = MissionManagerNode()
    # Auto-start mission in simulation (remove for hardware — call start_mission() externally)
    node.create_timer(3.0, lambda: node.start_mission())
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
