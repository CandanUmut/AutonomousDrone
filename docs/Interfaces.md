# Interfaces (v2)

## MAVLink / MAVSDK boundary

- Companion stack uses MAVSDK for all telemetry and command interfaces.
- Connection string is configured in YAML (`connection.system_address`).
- MAVSDK modules live in `software/companion/src/drone_platform/mavlink`.

## Config schema

See `software/companion/src/drone_platform/config/schema.md` for full YAML
schema, including mission parameters and safety gating fields.

## Safety gates

- `safety.mode` is either `sim` or `hardware`.
- `safety.allow_hardware` must be true **and** the CLI must pass
  `--allow-hardware` to unlock hardware mode.

## ROS2 (optional)

ROS2 is a future integration point (see `software/companion/ros2/README.md`).
