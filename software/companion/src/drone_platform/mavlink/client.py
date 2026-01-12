from __future__ import annotations

import asyncio
import logging

from mavsdk import System

from drone_platform.common.types import ConnectionConfig

logger = logging.getLogger(__name__)


class MavlinkClient:
    def __init__(self, connection: ConnectionConfig) -> None:
        self._connection = connection
        self.system = System()

    async def connect(self) -> None:
        logger.info("Connecting to MAVSDK at %s", self._connection.system_address)
        await self.system.connect(system_address=self._connection.system_address)

    async def wait_for_heartbeat(self, timeout_s: float = 30.0) -> None:
        logger.info("Waiting for heartbeat")
        async def _wait() -> None:
            async for state in self.system.core.connection_state():
                if state.is_connected:
                    logger.info("Heartbeat received")
                    return
                await asyncio.sleep(0.1)

        try:
            await asyncio.wait_for(_wait(), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            raise TimeoutError("Heartbeat timeout") from exc
