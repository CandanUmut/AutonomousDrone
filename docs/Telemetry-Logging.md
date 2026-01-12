# Telemetry & Logging (v2)

## What we log

- Mission state transitions
- MAVSDK connection status
- Mission progress updates
- Safety gating banner (SIM only)

## Log format

Logs are JSON-formatted by default, with fields:

- `timestamp`
- `level`
- `logger`
- `message`

## Log location

Logs are written to `software/logs/mission.log` (directory is gitignored).
