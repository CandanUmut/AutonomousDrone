#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-software/companion/src/drone_platform/config/default.yaml}"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Config not found at $CONFIG_PATH" >&2
  exit 1
fi

echo "Running mission demo with config: $CONFIG_PATH"

drone-platform mission-demo --config "$CONFIG_PATH"
