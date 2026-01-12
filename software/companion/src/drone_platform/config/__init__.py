from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from drone_platform.common.types import (
    AppConfig,
    ConnectionConfig,
    GeofenceConfig,
    LoggingConfig,
    MissionConfig,
    SafetyConfig,
    Waypoint,
)


def default_config_path() -> Path:
    return Path(__file__).with_name("default.yaml")


def load_config(path: Path) -> AppConfig:
    data = yaml.safe_load(path.read_text())
    return parse_config(data)


def parse_config(data: dict[str, Any]) -> AppConfig:
    connection = ConnectionConfig(system_address=data["connection"]["system_address"])
    mission_data = data["mission"]
    waypoints = [Waypoint(**wp) for wp in mission_data["waypoints"]]
    mission = MissionConfig(
        takeoff_alt_m=float(mission_data["takeoff_alt_m"]),
        rtl_alt_m=float(mission_data["rtl_alt_m"]),
        waypoints=waypoints,
    )
    geofence_data = data["geofence"]
    geofence = GeofenceConfig(
        center_lat=float(geofence_data["center_lat"]),
        center_lon=float(geofence_data["center_lon"]),
        radius_m=float(geofence_data["radius_m"]),
        min_alt_m=float(geofence_data["min_alt_m"]),
        max_alt_m=float(geofence_data["max_alt_m"]),
    )
    safety_data = data["safety"]
    safety = SafetyConfig(
        mode=safety_data["mode"],
        allow_hardware=bool(safety_data["allow_hardware"]),
        sim_only_banner=bool(safety_data["sim_only_banner"]),
    )
    logging_data = data["logging"]
    logging_config = LoggingConfig(
        level=logging_data["level"],
        log_dir=logging_data["log_dir"],
        json=bool(logging_data["json"]),
    )
    return AppConfig(
        connection=connection,
        mission=mission,
        geofence=geofence,
        safety=safety,
        logging=logging_config,
    )
