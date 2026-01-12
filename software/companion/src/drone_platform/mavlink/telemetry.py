from __future__ import annotations

import logging

from drone_platform.mavlink.client import MavlinkClient

logger = logging.getLogger(__name__)


async def wait_for_position(client: MavlinkClient) -> None:
    async for position in client.system.telemetry.position():
        logger.info(
            "Position lat=%.6f lon=%.6f alt=%.2f",
            position.latitude_deg,
            position.longitude_deg,
            position.relative_altitude_m,
        )
        return
