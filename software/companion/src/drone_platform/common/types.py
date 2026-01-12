from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Waypoint:
    lat: float
    lon: float
    alt_m: float


@dataclass(frozen=True)
class ConnectionConfig:
    system_address: str


@dataclass(frozen=True)
class MissionConfig:
    takeoff_alt_m: float
    rtl_alt_m: float
    waypoints: list[Waypoint]


@dataclass(frozen=True)
class GeofenceConfig:
    center_lat: float
    center_lon: float
    radius_m: float
    min_alt_m: float
    max_alt_m: float


@dataclass(frozen=True)
class SafetyConfig:
    mode: str
    allow_hardware: bool
    sim_only_banner: bool


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    log_dir: str
    json: bool


@dataclass(frozen=True)
class AppConfig:
    connection: ConnectionConfig
    mission: MissionConfig
    geofence: GeofenceConfig
    safety: SafetyConfig
    logging: LoggingConfig


class ActionHandler(Protocol):
    async def arm(self) -> None: ...

    async def takeoff(self, altitude_m: float) -> None: ...

    async def land(self) -> None: ...

    async def return_to_launch(self) -> None: ...

    async def wait_for_landed(self) -> None: ...


class MissionHandler(Protocol):
    async def upload_mission(self, waypoints: list[Waypoint], rtl_alt_m: float) -> None: ...

    async def start_mission(self) -> None: ...

    async def wait_for_mission_complete(self) -> None: ...
