from __future__ import annotations

import logging

from mavsdk import mission

from drone_platform.common.types import MissionHandler, Waypoint
from drone_platform.mavlink.client import MavlinkClient

logger = logging.getLogger(__name__)


def build_mission_items(waypoints: list[Waypoint]) -> list[mission.MissionItem]:
    items = []
    for waypoint in waypoints:
        items.append(
            mission.MissionItem(
                waypoint.lat,
                waypoint.lon,
                waypoint.alt_m,
                speed_m_s=5.0,
                is_fly_through=True,
                gimbal_pitch_deg=0.0,
                gimbal_yaw_deg=0.0,
                camera_action=mission.MissionItem.CameraAction.NONE,
            )
        )
    return items


class MavlinkMissionHandler(MissionHandler):
    def __init__(self, client: MavlinkClient) -> None:
        self._client = client

    async def upload_mission(self, waypoints: list[Waypoint], rtl_alt_m: float) -> None:
        items = build_mission_items(waypoints)
        logger.info("Uploading %d mission items", len(items))
        await self._client.system.mission.set_return_to_launch_after_mission(True)
        await self._client.system.mission.set_return_to_launch_altitude(rtl_alt_m)
        await self._client.system.mission.upload_mission(mission.MissionPlan(items))

    async def start_mission(self) -> None:
        logger.info("Starting mission")
        await self._client.system.mission.start_mission()

    async def wait_for_mission_complete(self) -> None:
        async for progress in self._client.system.mission.mission_progress():
            logger.info("Mission progress %d/%d", progress.current, progress.total)
            if progress.current == progress.total:
                logger.info("Mission complete")
                return
