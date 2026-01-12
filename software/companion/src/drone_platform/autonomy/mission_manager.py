from __future__ import annotations

import enum
import logging
from collections.abc import Callable

from drone_platform.common.types import ActionHandler, AppConfig, MissionHandler
from drone_platform.common.safety import ensure_sim_or_approved, validate_mission

logger = logging.getLogger(__name__)


class MissionState(enum.StrEnum):
    IDLE = "idle"
    CONNECTING = "connecting"
    ARMED = "armed"
    TAKING_OFF = "taking_off"
    MISSION = "mission"
    RETURNING = "returning"
    LANDING = "landing"
    COMPLETE = "complete"
    FAILED = "failed"


class MissionManager:
    def __init__(
        self,
        config: AppConfig,
        actions: ActionHandler,
        mission_handler: MissionHandler,
        on_state_change: Callable[[MissionState], None] | None = None,
    ) -> None:
        self._config = config
        self._actions = actions
        self._mission_handler = mission_handler
        self._state = MissionState.IDLE
        self._on_state_change = on_state_change

    @property
    def state(self) -> MissionState:
        return self._state

    def _set_state(self, state: MissionState) -> None:
        logger.info("State transition %s -> %s", self._state, state)
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    async def run(self) -> None:
        ensure_sim_or_approved(self._config)
        validate_mission(self._config)

        try:
            self._set_state(MissionState.CONNECTING)
            self._set_state(MissionState.ARMED)
            await self._actions.arm()

            self._set_state(MissionState.TAKING_OFF)
            await self._actions.takeoff(self._config.mission.takeoff_alt_m)

            await self._mission_handler.upload_mission(
                self._config.mission.waypoints,
                self._config.mission.rtl_alt_m,
            )
            self._set_state(MissionState.MISSION)
            await self._mission_handler.start_mission()
            await self._mission_handler.wait_for_mission_complete()

            self._set_state(MissionState.RETURNING)
            await self._actions.return_to_launch()

            self._set_state(MissionState.LANDING)
            await self._actions.wait_for_landed()

            self._set_state(MissionState.COMPLETE)
        except Exception:
            logger.exception("Mission failed")
            self._set_state(MissionState.FAILED)
            raise
