from __future__ import annotations

import logging

from mavsdk import telemetry

from drone_platform.common.types import ActionHandler
from drone_platform.mavlink.client import MavlinkClient

logger = logging.getLogger(__name__)


class MavlinkActionHandler(ActionHandler):
    def __init__(self, client: MavlinkClient) -> None:
        self._client = client

    async def arm(self) -> None:
        logger.info("Arming")
        await self._client.system.action.arm()

    async def takeoff(self, altitude_m: float) -> None:
        logger.info("Setting takeoff altitude %.1f m", altitude_m)
        await self._client.system.action.set_takeoff_altitude(altitude_m)
        logger.info("Takeoff")
        await self._client.system.action.takeoff()

    async def land(self) -> None:
        logger.info("Landing")
        await self._client.system.action.land()

    async def return_to_launch(self) -> None:
        logger.info("Return to launch")
        await self._client.system.action.return_to_launch()

    async def wait_for_landed(self) -> None:
        async for landed_state in self._client.system.telemetry.landed_state():
            if landed_state is telemetry.LandedState.ON_GROUND:
                logger.info("Landed confirmed")
                return
