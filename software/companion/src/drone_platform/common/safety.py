from __future__ import annotations

import logging

from drone_platform.common.types import AppConfig
from drone_platform.autonomy.geofence import Geofence

logger = logging.getLogger(__name__)


class SafetyError(RuntimeError):
    pass


def ensure_sim_or_approved(config: AppConfig) -> None:
    mode = config.safety.mode.lower()
    if mode != "sim" and not config.safety.allow_hardware:
        raise SafetyError(
            "Hardware mode blocked. Set safety.allow_hardware=true and pass --allow-hardware."
        )
    if mode == "sim":
        logger.info("SIM mode enabled. Hardware outputs are gated.")


def validate_mission(config: AppConfig) -> None:
    geofence = Geofence.from_config(config.geofence)
    for idx, waypoint in enumerate(config.mission.waypoints, start=1):
        if not geofence.contains(waypoint.lat, waypoint.lon, waypoint.alt_m):
            raise SafetyError(f"Waypoint {idx} is outside the geofence.")

    if config.mission.takeoff_alt_m < config.geofence.min_alt_m:
        raise SafetyError("Takeoff altitude below geofence minimum.")

    if config.mission.takeoff_alt_m > config.geofence.max_alt_m:
        raise SafetyError("Takeoff altitude above geofence maximum.")

    if config.mission.rtl_alt_m > config.geofence.max_alt_m:
        raise SafetyError("RTL altitude above geofence maximum.")
