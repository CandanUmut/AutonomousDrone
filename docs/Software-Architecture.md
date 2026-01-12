# Software Architecture (v2)

## Overview

The companion stack is a Python-first runtime that connects to PX4 SITL via
MAVSDK and executes a mission manager state machine with safety gating.

```
CLI -> Config -> Safety -> Mission Manager
                  |-> MAVSDK Actions
                  |-> MAVSDK Missions
                  |-> Telemetry streams
```

## Modules

- `software/companion/src/drone_platform/cli`
  - CLI entrypoints (mission demo, future tools).
- `software/companion/src/drone_platform/config`
  - YAML config loader and schema.
- `software/companion/src/drone_platform/common`
  - Logging, time helpers, safety gates, shared types.
- `software/companion/src/drone_platform/mavlink`
  - MAVSDK wrapper for connection, telemetry, actions, and missions.
- `software/companion/src/drone_platform/autonomy`
  - Mission manager state machine and behavior stubs.
- `software/companion/src/drone_platform/perception`
  - Interfaces only (no perception implementation in v2).
- `software/companion/src/drone_platform/comms`
  - Link status stubs and future comms integration.
- `software/companion/src/drone_platform/fleet`
  - Fleet stubs for future multi-vehicle coordination.

## Data flow

1. CLI loads config, sets up logging, and enforces SIM gating.
2. MAVSDK connects to SITL and waits for heartbeat.
3. Mission manager validates the mission against geofence rules.
4. Actions: arm → takeoff → upload mission → start mission → RTL → land.

## Safety guardrails

- SIM-only configuration by default.
- Geofence validation for waypoint missions.
- Explicit operator override for hardware mode.
