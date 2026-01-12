import asyncio

from drone_platform.autonomy.mission_manager import MissionManager, MissionState
from drone_platform.common.types import (
    ActionHandler,
    AppConfig,
    ConnectionConfig,
    GeofenceConfig,
    LoggingConfig,
    MissionConfig,
    SafetyConfig,
    Waypoint,
)


class FakeActions(ActionHandler):
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def arm(self) -> None:
        self.calls.append("arm")

    async def takeoff(self, altitude_m: float) -> None:
        self.calls.append(f"takeoff:{altitude_m}")

    async def land(self) -> None:
        self.calls.append("land")

    async def return_to_launch(self) -> None:
        self.calls.append("rtl")

    async def wait_for_landed(self) -> None:
        self.calls.append("landed")


class FakeMissionHandler:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def upload_mission(self, waypoints, rtl_alt_m) -> None:
        self.calls.append(f"upload:{len(waypoints)}:{rtl_alt_m}")

    async def start_mission(self) -> None:
        self.calls.append("start")

    async def wait_for_mission_complete(self) -> None:
        self.calls.append("complete")


def build_config() -> AppConfig:
    return AppConfig(
        connection=ConnectionConfig(system_address="udp://:14540"),
        mission=MissionConfig(
            takeoff_alt_m=10.0,
            rtl_alt_m=15.0,
            waypoints=[
                Waypoint(lat=47.0, lon=8.0, alt_m=10.0),
                Waypoint(lat=47.0, lon=8.001, alt_m=10.0),
            ],
        ),
        geofence=GeofenceConfig(
            center_lat=47.0,
            center_lon=8.0,
            radius_m=500.0,
            min_alt_m=0.0,
            max_alt_m=120.0,
        ),
        safety=SafetyConfig(mode="sim", allow_hardware=False, sim_only_banner=True),
        logging=LoggingConfig(level="INFO", log_dir="software/logs", json=True),
    )


def test_mission_manager_state_machine() -> None:
    config = build_config()
    actions = FakeActions()
    missions = FakeMissionHandler()
    manager = MissionManager(config, actions, missions)

    asyncio.run(manager.run())

    assert manager.state is MissionState.COMPLETE
    assert actions.calls[0] == "arm"
    assert "takeoff" in actions.calls[1]
    assert missions.calls[0].startswith("upload")
