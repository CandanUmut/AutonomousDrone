# Developer Setup (v2)

> **Safety-first:** This repository is SIM-first. Do not use these instructions
> to operate real aircraft. Always follow local laws and regulations. This is
> not legal advice.

## Supported OS

- **Recommended:** Linux (Ubuntu 22.04+) or macOS (13+)
- **Windows:** WSL2 is supported for the Python stack. PX4 SITL runs best in
  Linux; use WSL2 + GUI forwarding or run SITL on a separate Linux host.

## Option A — Docker (preferred)

1. Install Docker Desktop.
2. Build the dev image:

```bash
docker build -f docker/Dockerfile.dev -t drone-platform-dev .
```

3. Run a shell in the container:

```bash
docker run --rm -it --network host -v "$PWD":/workspace drone-platform-dev
```

Optional (docker-compose):

```bash
docker compose -f docker/docker-compose.yml up --build
```

4. In another terminal, start PX4 SITL (see "PX4 SITL" below).
5. Run the mission demo:

```bash
drone-platform mission-demo --config software/companion/src/drone_platform/config/default.yaml
```

## Option B — Native (optional)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e software/companion[dev]
```

## PX4 SITL

We support **PX4 SITL** as the default simulator. If you already have PX4 built,
export the path and run the helper script:

```bash
export PX4_DIR=~/src/PX4-Autopilot
./scripts/sim_px4.sh
```

If you do not have PX4 installed, follow the official PX4 SITL guide and then
return here. Keep SITL running while you run the mission demo.

## One-command mission demo

```bash
./scripts/run_mission_demo.sh
```

This runs the default mission in `software/companion/src/drone_platform/config/default.yaml`.

## Useful make targets

```bash
make setup
make sim
make mission
make test
make lint
```

## Troubleshooting

- **No heartbeat:** ensure SITL is running and the UDP port matches the config.
- **MAVSDK connection issues:** verify firewall settings and `udp://:14540`.
