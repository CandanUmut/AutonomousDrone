# Companion Stack (v2)

Python-first companion stack for MAVSDK control, autonomy logic, and safety gating.

## Quick start (SIM)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e software/companion[dev]

# Run mission demo (requires PX4 SITL running)
drone-platform mission-demo --config software/companion/src/drone_platform/config/default.yaml
```

## Architecture overview

- **CLI**: `drone_platform.cli.main` provides mission entrypoints.
- **MAVLink layer**: `drone_platform.mavlink` wraps MAVSDK.
- **Autonomy**: `drone_platform.autonomy` contains the mission manager and behaviors.
- **Safety**: `drone_platform.common.safety` enforces SIM gating and geofence checks.
- **Config**: `drone_platform.config` loads YAML configuration.

## Configuration

See `src/drone_platform/config/schema.md` for the full schema. Default config is
`src/drone_platform/config/default.yaml`.

## Logging

Logs are structured JSON by default and written to `software/logs/mission.log`.

## Safety gating

The mission demo runs in **SIM mode** by default. Hardware mode is blocked unless
`allow_hardware` is true in the config **and** you pass `--allow-hardware`.

## ROS2 (optional)

See `ros2/README.md` for lightweight bridge notes and a stub package outline.
