# Sprint 01

## Goals
- Establish SIM-first mission demo with safety gates
- Stand up companion stack structure

## Deliverables
- Companion package skeleton with mission manager
- PX4 SITL scripts and mission demo script
- Dev setup documentation

## Acceptance criteria
- Mission demo connects to SITL and flies a waypoint loop
- Safety gating blocks hardware mode without explicit override
- Logs written to `software/logs/mission.log`

## Demo definition
- Run `make sim` and `make mission` on a fresh clone
