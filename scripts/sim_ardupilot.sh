#!/usr/bin/env bash
# sim_ardupilot.sh — Launch ArduCopter SITL with Gazebo integration
#
# Prerequisites:
#   - ArduPilot source at $ARDUPILOT_DIR (default: ~/ardupilot)
#   - ardupilot_gazebo plugin built and on GAZEBO_PLUGIN_PATH
#   - Gazebo 11 installed (gazebo --version)
#
# Usage:
#   ./scripts/sim_ardupilot.sh [--lat 47.397742] [--lon 8.545594] [--alt 488]
#
# After this script starts:
#   1. In a new terminal: ros2 launch delivery_drone simulation.launch.py
#   2. In another terminal: ros2 topic echo /drone/mission/state

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────
ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
VEHICLE="ArduCopter"
FRAME="++"        # X-configuration quad
SPEEDUP=1         # Simulation speed (1 = realtime)

# Home location (default: Zurich Kloten airport area — matches default.yaml)
LAT="47.397742"
LON="8.545594"
ALT="488"          # Altitude AMSL in metres

# Gazebo model path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODEL_DIR="$REPO_ROOT/simulation/gazebo/models"
WORLD_FILE="$REPO_ROOT/simulation/gazebo/worlds/delivery_urban.world"

# ── Argument parsing ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --lat) LAT="$2"; shift 2 ;;
        --lon) LON="$2"; shift 2 ;;
        --alt) ALT="$2"; shift 2 ;;
        --speedup) SPEEDUP="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Checks ──────────────────────────────────────────────────────────────────
if [[ ! -d "$ARDUPILOT_DIR" ]]; then
    cat <<EOF
ERROR: ArduPilot directory not found at: $ARDUPILOT_DIR

Clone ArduPilot:
    git clone --recursive https://github.com/ArduPilot/ardupilot.git ~/ardupilot
    cd ~/ardupilot && ./waf configure --board sitl && ./waf copter

Then re-run this script or set ARDUPILOT_DIR.
EOF
    exit 1
fi

if ! command -v gazebo &>/dev/null; then
    echo "ERROR: Gazebo not found. Install with:"
    echo "  sudo apt install gazebo11 ros-humble-gazebo-ros-pkgs"
    exit 1
fi

# ── Gazebo environment ───────────────────────────────────────────────────────
export GAZEBO_MODEL_PATH="$MODEL_DIR:${GAZEBO_MODEL_PATH:-}"
export GAZEBO_PLUGIN_PATH="${GAZEBO_PLUGIN_PATH:-/usr/lib/x86_64-linux-gnu/gazebo-11/plugins}"

# ardupilot_gazebo plugin (built separately)
AP_GAZEBO_PLUGIN="${AP_GAZEBO_PLUGIN:-$HOME/ardupilot_gazebo/build}"
if [[ -d "$AP_GAZEBO_PLUGIN" ]]; then
    export GAZEBO_PLUGIN_PATH="$AP_GAZEBO_PLUGIN:$GAZEBO_PLUGIN_PATH"
else
    echo "WARNING: ardupilot_gazebo plugin not found at $AP_GAZEBO_PLUGIN"
    echo "  Build it: https://github.com/ArduPilot/ardupilot_gazebo"
fi

echo "══════════════════════════════════════════════════════"
echo " ArduCopter SITL + Gazebo Delivery Simulation"
echo "══════════════════════════════════════════════════════"
echo " ArduPilot: $ARDUPILOT_DIR"
echo " Home:      $LAT, $LON (alt: $ALT m)"
echo " World:     $WORLD_FILE"
echo " Speed:     ${SPEEDUP}×"
echo "══════════════════════════════════════════════════════"

# ── Launch ArduCopter SITL ────────────────────────────────────────────────────
cd "$ARDUPILOT_DIR/ArduCopter"

# SITL parameters:
#   -v Vehicle   -f Frame   -S Speedup   --home lat,lon,alt,heading
#   --model gazebo    Use Gazebo as FDM (physics engine)
#   -I 0         Instance 0 (ports 5760 for MAVProxy, 9002/9003 for Gazebo)
"$ARDUPILOT_DIR/Tools/autotest/sim_vehicle.py" \
    -v "$VEHICLE" \
    -f "$FRAME" \
    -S "$SPEEDUP" \
    --home "$LAT,$LON,$ALT,0" \
    --model gazebo \
    -I 0 \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551 \
    --console \
    --map \
    --add-param-file="$REPO_ROOT/simulation/ardupilot/copter_delivery.parm" \
    "$@"
