#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PX4_DIR:-}" ]]; then
  echo "PX4_DIR is not set. Please export PX4_DIR=/path/to/PX4-Autopilot" >&2
  exit 1
fi

cd "$PX4_DIR"

echo "Starting PX4 SITL (gazebo)"
make px4_sitl_default gazebo
