# PX4 SITL

PX4 SITL is the default simulator for the companion stack.

## Bring-your-own SITL

1. Install PX4 following the official documentation.
2. Export the PX4 path:

```bash
export PX4_DIR=~/src/PX4-Autopilot
```

3. Start SITL (from the repo root):

```bash
./scripts/sim_px4.sh
```

## Mission demo

With SITL running in another terminal:

```bash
./scripts/run_mission_demo.sh
```

This connects to `udp://:14540` by default.
