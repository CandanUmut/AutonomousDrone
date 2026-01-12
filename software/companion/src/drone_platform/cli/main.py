from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from pathlib import Path

import typer

from drone_platform.autonomy.mission_manager import MissionManager
from drone_platform.common.logging import log_banner, setup_logging
from drone_platform.common.safety import ensure_sim_or_approved, validate_mission
from drone_platform.common.types import AppConfig
from drone_platform.config import default_config_path, load_config
from drone_platform.mavlink.actions import MavlinkActionHandler
from drone_platform.mavlink.client import MavlinkClient
from drone_platform.mavlink.missions import MavlinkMissionHandler

app = typer.Typer(help="Drone Platform companion CLI")


@app.command()
def mission_demo(
    config: Path = typer.Option(default_config_path(), help="Path to config YAML"),
    allow_hardware: bool = typer.Option(False, help="Override safety gate for hardware"),
) -> None:
    """Run the simulated mission demo."""
    cfg = load_config(config)
    if cfg.safety.mode != "sim":
        if not allow_hardware:
            raise typer.BadParameter(
                "Hardware mode requires --allow-hardware and safety.allow_hardware=true."
            )
        if not cfg.safety.allow_hardware:
            raise typer.BadParameter(
                "Set safety.allow_hardware=true in the config before using --allow-hardware."
            )
        cfg = replace(cfg, safety=replace(cfg.safety, allow_hardware=True))

    setup_logging(cfg.logging)
    logger = logging.getLogger(__name__)

    if cfg.safety.sim_only_banner:
        log_banner("SIM ONLY - DO NOT USE WITH REAL HARDWARE", logger=logger)

    asyncio.run(_run_mission(cfg))


def main() -> None:
    app()


async def _run_mission(cfg: AppConfig) -> None:
    ensure_sim_or_approved(cfg)
    validate_mission(cfg)

    client = MavlinkClient(cfg.connection)
    await client.connect()
    await client.wait_for_heartbeat()

    actions = MavlinkActionHandler(client)
    missions = MavlinkMissionHandler(client)

    manager = MissionManager(cfg, actions, missions)
    await manager.run()


if __name__ == "__main__":
    main()
