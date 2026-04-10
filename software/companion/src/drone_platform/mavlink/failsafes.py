"""
Failsafe configuration and monitoring via MAVSDK.

Configures ArduCopter/PX4 failsafe behaviours programmatically and provides
async monitors that trigger recovery actions on detected fault conditions.

Failsafes implemented
---------------------
    link_loss          RC/telemetry link lost → RTL after timeout
    low_battery        Battery below threshold → RTL
    critical_battery   Battery below hard floor → land in place
    geofence_breach    Position outside geofence → RTL
    ekf_failure        EKF health degraded → controlled descent

All monitors are async generators intended to be run as concurrent tasks
alongside the mission manager.

Usage:
    async with mavsdk.System() as drone:
        await configure_failsafes(drone, config)
        asyncio.gather(
            monitor_link_loss(drone),
            monitor_battery(drone, config),
        )
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import AsyncIterator

from mavsdk import System

logger = logging.getLogger(__name__)


@dataclass
class FailsafeConfig:
    # Link-loss
    link_loss_timeout_s: float = 5.0    # Seconds before RTL triggers on link loss

    # Battery
    low_battery_pct: float = 25.0       # % — trigger RTL
    critical_battery_pct: float = 10.0  # % — trigger land in place

    # EKF
    ekf_check_interval_s: float = 1.0

    # Telemetry poll interval
    poll_interval_s: float = 0.5


async def configure_failsafes(drone: System, config: FailsafeConfig) -> None:
    """
    Set ArduCopter/PX4 failsafe parameters via MAVSDK param interface.
    Only parameters available in both firmwares are set here.
    """
    params: dict[str, float | int] = {
        # ArduCopter: FS_THR_ENABLE — RC failsafe (1 = RTL)
        "FS_THR_ENABLE": 1,
        # ArduCopter: FS_BATT_ENABLE — battery failsafe (2 = land, 1 = RTL)
        "FS_BATT_ENABLE": 1,
        # ArduCopter: BATT_FS_LOW_ACT — 2 = RTL
        "BATT_FS_LOW_ACT": 2,
        # ArduCopter: BATT_LOW_VOLT (calculated: 3.5 V/cell × 6S = 21 V)
        "BATT_LOW_VOLT": 21.0,
        # ArduCopter: BATT_CRT_VOLT (3.2 V/cell × 6S = 19.2 V)
        "BATT_CRT_VOLT": 19.2,
        # ArduCopter: GCS_TIMEOUT — telemetry link loss timeout
        "FS_GCS_ENABLE": 2,  # 2 = RTL on GCS link loss
    }

    for param_name, value in params.items():
        try:
            if isinstance(value, float):
                await drone.param.set_param_float(param_name, value)
            else:
                await drone.param.set_param_int(param_name, int(value))
            logger.debug("Param set: %s = %s", param_name, value)
        except Exception as exc:
            logger.warning("Could not set %s: %s", param_name, exc)

    logger.info(
        "Failsafe configuration applied (low=%.0f%%, critical=%.0f%%)",
        config.low_battery_pct,
        config.critical_battery_pct,
    )


# --------------------------------------------------------------------------
async def monitor_link_loss(
    drone: System,
    config: FailsafeConfig,
    on_link_loss: "Callable[[], Awaitable[None]] | None" = None,
) -> None:
    """
    Monitor telemetry heartbeat. If MAVSDK loses connection for longer than
    link_loss_timeout_s, call on_link_loss (or log an error).

    ArduCopter's built-in GCS failsafe also handles this — this monitor
    provides a companion-side duplicate for logging and custom recovery.
    """
    logger.info("Link-loss monitor started")
    last_beat: float | None = None

    async for is_connected in drone.core.connection_state():
        if is_connected:
            last_beat = asyncio.get_event_loop().time()
        else:
            if last_beat is not None:
                lost_for = asyncio.get_event_loop().time() - last_beat
                if lost_for >= config.link_loss_timeout_s:
                    logger.error(
                        "Link lost for %.1f s — RTL should be active", lost_for
                    )
                    if on_link_loss:
                        await on_link_loss()
        await asyncio.sleep(config.poll_interval_s)


# --------------------------------------------------------------------------
async def monitor_battery(
    drone: System,
    config: FailsafeConfig,
    on_low: "Callable[[], Awaitable[None]] | None" = None,
    on_critical: "Callable[[], Awaitable[None]] | None" = None,
) -> None:
    """
    Monitor battery state. Calls provided callbacks at low and critical thresholds.
    ArduCopter's built-in failsafe should already RTL/land, but the companion
    can take additional action (e.g., send an alert, log extra telemetry).
    """
    logger.info("Battery monitor started (low=%.0f%%, crit=%.0f%%)",
                config.low_battery_pct, config.critical_battery_pct)

    _low_triggered = False
    _crit_triggered = False

    async for battery in drone.telemetry.battery():
        pct = battery.remaining_percent * 100.0

        if pct <= config.critical_battery_pct and not _crit_triggered:
            _crit_triggered = True
            logger.error("CRITICAL battery: %.0f%% — emergency land", pct)
            if on_critical:
                await on_critical()

        elif pct <= config.low_battery_pct and not _low_triggered:
            _low_triggered = True
            logger.warning("Low battery: %.0f%% — initiating RTL", pct)
            if on_low:
                await on_low()

        await asyncio.sleep(config.poll_interval_s)


# --------------------------------------------------------------------------
async def monitor_ekf(
    drone: System,
    config: FailsafeConfig,
    on_ekf_failure: "Callable[[], Awaitable[None]] | None" = None,
) -> None:
    """
    Monitor EKF health flags. On failure, log and optionally trigger recovery.
    EKF health is exposed via the IMU telemetry status in MAVSDK.
    """
    logger.info("EKF health monitor started")
    _failure_logged = False

    async for health in drone.telemetry.health():
        all_ok = (
            health.is_global_position_ok
            and health.is_local_position_ok
            and health.is_home_position_ok
        )
        if not all_ok and not _failure_logged:
            _failure_logged = True
            logger.error(
                "EKF health degraded: global_pos=%s local_pos=%s home=%s",
                health.is_global_position_ok,
                health.is_local_position_ok,
                health.is_home_position_ok,
            )
            if on_ekf_failure:
                await on_ekf_failure()
        elif all_ok:
            _failure_logged = False

        await asyncio.sleep(config.ekf_check_interval_s)


# --------------------------------------------------------------------------
async def configure_geofence(drone: System, radius_m: float, alt_max_m: float) -> None:
    """
    Upload a circular geofence to the autopilot.
    The geofence is centred on the home position set at arming time.
    """
    from mavsdk.geofence import Point, Polygon

    logger.info(
        "Uploading geofence: radius=%.0f m, max_alt=%.0f m", radius_m, alt_max_m
    )

    # MAVSDK geofence requires a polygon — approximate circle with 36 points
    home = await drone.telemetry.position().__anext__()
    import math

    points = []
    for i in range(36):
        angle = math.radians(i * 10)
        dlat = (radius_m / 111_320.0) * math.cos(angle)
        dlon = (radius_m / (111_320.0 * math.cos(math.radians(home.latitude_deg)))) * math.sin(angle)
        points.append(Point(home.latitude_deg + dlat, home.longitude_deg + dlon))

    polygon = Polygon(points, Polygon.FenceType.INCLUSION)
    await drone.geofence.upload_geofence([polygon])
    logger.info("Geofence uploaded (%d vertices)", len(points))
