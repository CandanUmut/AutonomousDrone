"""
Battery swap station logic for the MAVSDK companion stack.

This module manages the hot-swap lifecycle:
    1. Approach swap station at cruise altitude
    2. Enable ArUco precision landing
    3. Descend and land guided by ArUco offset corrections
    4. Disarm on touchdown
    5. Signal station controller to perform swap (GPIO or serial)
    6. Wait for station to confirm swap is complete
    7. Verify new battery voltage is adequate
    8. Arm and continue mission

Station interface
-----------------
The station controller (e.g., Arduino Nano) communicates over serial or,
in simulation, via shared memory / ROS topic bridge.

In simulation mode the swap is simulated with a configurable delay.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class SwapState(StrEnum):
    IDLE = "idle"
    APPROACHING = "approaching"
    DESCENDING = "descending"
    LANDED = "landed"
    SWAP_REQUESTED = "swap_requested"
    SWAP_IN_PROGRESS = "swap_in_progress"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class SwapConfig:
    sim_mode: bool = True
    sim_swap_delay_s: float = 10.0     # How long to simulate the swap
    min_voltage_per_cell: float = 3.9  # Minimum acceptable fresh battery
    cell_count: int = 6
    swap_timeout_s: float = 300.0
    verification_polls: int = 5        # How many times to check voltage
    serial_port: str = "/dev/ttyUSB1"  # For real hardware station interface
    serial_baud: int = 115200


class BatterySwapManager:
    """
    Manages the complete battery swap lifecycle.
    Designed to be called from the MAVSDK mission manager when the drone
    has landed at the swap station.
    """

    SWAP_REQUEST_BYTE = b"\x01"
    SWAP_READY_BYTE = b"\x02"

    def __init__(self, config: SwapConfig | None = None) -> None:
        self._config = config or SwapConfig()
        self._state = SwapState.IDLE

    @property
    def state(self) -> SwapState:
        return self._state

    def _set_state(self, state: SwapState) -> None:
        logger.info("Swap: %s → %s", self._state, state)
        self._state = state

    # ------------------------------------------------------------------
    async def run_swap(
        self,
        get_battery_voltage_fn: "Callable[[], Awaitable[float]] | None" = None,
    ) -> bool:
        """
        Execute a full hot-swap cycle.

        Args:
            get_battery_voltage_fn: Async callable that returns pack voltage (V).
                                    If None, voltage verification is skipped.

        Returns:
            True if swap was successful and battery is adequate.
        """
        self._set_state(SwapState.SWAP_REQUESTED)

        if self._config.sim_mode:
            success = await self._sim_swap()
        else:
            success = await self._hw_swap()

        if not success:
            self._set_state(SwapState.FAILED)
            return False

        self._set_state(SwapState.VERIFYING)
        if get_battery_voltage_fn is not None:
            ok = await self._verify_voltage(get_battery_voltage_fn)
            if not ok:
                self._set_state(SwapState.FAILED)
                logger.error("Swap failed: battery voltage too low after swap")
                return False

        self._set_state(SwapState.COMPLETE)
        logger.info("Battery swap complete — ready to fly")
        return True

    # ------------------------------------------------------------------
    async def _sim_swap(self) -> bool:
        """Simulate swap with a configurable delay."""
        logger.info(
            "SIM: Battery swap in progress (%.0f s)…",
            self._config.sim_swap_delay_s,
        )
        self._set_state(SwapState.SWAP_IN_PROGRESS)
        await asyncio.sleep(self._config.sim_swap_delay_s)
        logger.info("SIM: Swap complete")
        return True

    async def _hw_swap(self) -> bool:
        """
        Real hardware swap via serial interface to station Arduino.

        Protocol:
            Host sends:   0x01 (SWAP_REQUEST)
            Arduino does: release latch, remove old battery, insert new, close latch
            Arduino sends: 0x02 (SWAP_READY)
        """
        try:
            import serial  # type: ignore[import-untyped]
        except ImportError:
            logger.error("pyserial not installed — cannot perform hardware swap")
            return False

        try:
            ser = serial.Serial(
                self._config.serial_port,
                self._config.serial_baud,
                timeout=self._config.swap_timeout_s,
            )
        except serial.SerialException as exc:
            logger.error("Serial open failed: %s", exc)
            return False

        try:
            self._set_state(SwapState.SWAP_IN_PROGRESS)
            ser.write(self.SWAP_REQUEST_BYTE)
            logger.info("HW: Swap request sent to station controller")

            # Wait for completion byte
            response = ser.read(1)
            if response == self.SWAP_READY_BYTE:
                logger.info("HW: Station confirms swap complete")
                return True
            else:
                logger.error("HW: Unexpected response: %r", response)
                return False
        finally:
            ser.close()

    async def _verify_voltage(
        self,
        get_voltage_fn: "Callable[[], Awaitable[float]]",
    ) -> bool:
        """Poll voltage several times to confirm a good battery was installed."""
        min_pack_v = self._config.min_voltage_per_cell * self._config.cell_count

        for attempt in range(self._config.verification_polls):
            await asyncio.sleep(1.0)
            try:
                voltage = await get_voltage_fn()
            except Exception as exc:
                logger.warning("Voltage read failed (attempt %d): %s", attempt + 1, exc)
                continue

            cell_v = voltage / self._config.cell_count
            logger.info(
                "Verification %d/%d: %.2f V (%.2f V/cell, need ≥ %.2f)",
                attempt + 1,
                self._config.verification_polls,
                voltage,
                cell_v,
                self._config.min_voltage_per_cell,
            )
            if voltage >= min_pack_v:
                return True

        logger.error(
            "Battery voltage verification failed after %d attempts",
            self._config.verification_polls,
        )
        return False
