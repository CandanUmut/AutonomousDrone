# Safety

> **SIM-first policy:** all mission demos and automation flows are intended for
> simulation only. Do not use this repository to operate real aircraft. This is
> not legal advice.

## Safety-first principles
- Design to fail safe.
- Test in increasing complexity (simulation → bench → field).
- Maintain conservative operational limits.
- Separate autonomy software from real hardware until validated in SITL.

## SIM-only gating (v2)
- `mode: sim` is the default in configuration files.
- Hardware mode is blocked unless `allow_hardware: true` is explicitly set and
  the operator passes the `--allow-hardware` CLI flag.
- Mission demos log a **SIM ONLY** banner before takeoff in simulation.

## High-level kill-switch concept
- Manual override on the RC transmitter.
- Companion-side software abort command.
- Autopilot failsafes (RTL, land) configured via PX4 parameters.

## Prohibited use
- No weaponization or harmful payloads.
- No unsafe operations or violation of laws.

## Safety roles
- Pilot-in-command
- Safety officer
- Test lead
