# Simulation Setup Guide

End-to-end walkthrough for running the delivery drone simulation in Gazebo
with ArduCopter SITL and the ROS 2 autonomy stack.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Your machine                                           │
│                                                         │
│  ┌──────────────┐    UDP 9002/9003    ┌──────────────┐  │
│  │  ArduCopter  │◄──────────────────►│   Gazebo 11  │  │
│  │    SITL      │                    │  (physics +  │  │
│  └──────┬───────┘                    │   sensors)   │  │
│         │ UDP 14550 (MAVLink)        └──────────────┘  │
│  ┌──────▼───────┐                                       │
│  │    MAVROS    │  MAVLink ↔ ROS 2 bridge               │
│  └──────┬───────┘                                       │
│         │ ROS 2 topics                                  │
│  ┌──────▼────────────────────────────────────────────┐  │
│  │  delivery_drone ROS 2 nodes                       │  │
│  │   mission_manager  obstacle_avoidance             │  │
│  │   battery_monitor  precision_landing              │  │
│  │   payload_manager                                 │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. Operating System
Ubuntu 22.04 LTS (recommended). Other distros work but paths differ.

### 2. ROS 2 Humble
```bash
# Official install: https://docs.ros.org/en/humble/Installation.html
sudo apt install ros-humble-desktop ros-humble-mavros ros-humble-mavros-extras
# MAVLink geographiclib datasets (required by MAVROS)
sudo /opt/ros/humble/lib/mavros/install_geographiclib_datasets.sh
```

### 3. Gazebo 11 + ROS 2 bridge
```bash
sudo apt install gazebo11 ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control
```

### 4. ArduPilot SITL
```bash
git clone --recursive https://github.com/ArduPilot/ardupilot.git ~/ardupilot
cd ~/ardupilot
./Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile
./waf configure --board sitl
./waf copter         # builds ArduCopter SITL binary
```

### 5. ardupilot_gazebo plugin
```bash
git clone https://github.com/ArduPilot/ardupilot_gazebo.git ~/ardupilot_gazebo
cd ~/ardupilot_gazebo
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
# Plugin .so will be in ~/ardupilot_gazebo/build/
```

### 6. Python packages for the companion stack
```bash
cd /path/to/AutonomousDrone
pip install -e software/companion[dev]
pip install opencv-contrib-python pyserial  # for ArUco + hardware swap
```

### 7. Build the ROS 2 workspace
```bash
cd /path/to/AutonomousDrone/software/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

---

## Running the Simulation

Open **4 terminal windows**.

### Terminal 1 — ArduCopter SITL
```bash
cd /path/to/AutonomousDrone
./scripts/sim_ardupilot.sh
```
Wait for the MAVProxy console to show `APM: EKF3 IMU0 is using GPS` before
continuing. This confirms the EKF has initialised and the simulated GPS lock
is acquired.

### Terminal 2 — Gazebo + ROS 2 autonomy nodes
```bash
source /opt/ros/humble/setup.bash
source /path/to/AutonomousDrone/software/ros2_ws/install/setup.bash
export GAZEBO_MODEL_PATH=/path/to/AutonomousDrone/simulation/gazebo/models:$GAZEBO_MODEL_PATH
export GAZEBO_PLUGIN_PATH=~/ardupilot_gazebo/build:$GAZEBO_PLUGIN_PATH

ros2 launch delivery_drone simulation.launch.py
```

### Terminal 3 — Monitor mission state
```bash
source /opt/ros/humble/setup.bash
# Watch mission state machine
ros2 topic echo /drone/mission/state
# Or watch battery
ros2 topic echo /drone/battery/percentage
# Or watch VFH histogram (verbose)
ros2 topic echo /drone/vfh/histogram
```

### Terminal 4 — QGroundControl (optional visual monitor)
```bash
# Download from https://qgroundcontrol.com
# Connect UDP on port 14550 — it will auto-discover the SITL
./QGroundControl.AppImage
```

---

## Environment Variables
```bash
export ARDUPILOT_DIR=~/ardupilot
export GAZEBO_MODEL_PATH=/path/to/AutonomousDrone/simulation/gazebo/models
export GAZEBO_PLUGIN_PATH=~/ardupilot_gazebo/build
```
Add these to `~/.bashrc` to make them permanent.

---

## Expected Sequence

Once everything is running:

1. **T+0 s**: Mission manager starts, waits 3 s then calls `start_mission()`
2. **T+3 s**: PREFLIGHT checks (FC connected? GPS lock? Battery > 30%?)
3. **T+~8 s**: ARMING → sends arm command to ArduCopter
4. **T+~10 s**: TAKEOFF — climbs to 15 m cruise altitude
5. **T+~20 s**: NAVIGATING — VFH+ active, obstacle avoidance running, flying toward delivery point (80, 5)
6. **T+~60 s**: APPROACHING — within 20 m of delivery point, slowing down
7. **T+~70 s**: DELIVERING — payload release command sent, 5 s hover
8. **T+~75 s**: ASCENDING → RETURNING — climbing back to cruise alt, heading home
9. **T+~120 s**: APPROACH_STATION → PRECISION_LANDING — ArUco detection enabled
10. **T+~140 s**: LANDED — disarmed at swap station
11. **T+~141 s**: BATTERY_SWAP (if battery < 25%) or COMPLETE

---

## Tuning VFH+

If the drone gets stuck or oscillates near obstacles, adjust in `drone_params.yaml`:

| Parameter | Increase if... | Decrease if... |
|---|---|---|
| `threshold` | Too many false positives (stops unnecessarily) | Flies through real obstacles |
| `safety_radius_m` | Passes too close to obstacles | Cannot navigate narrow gaps |
| `max_speed_ms` | Navigation is too slow | Overshoots waypoints |
| `hysteresis_deg` | Oscillates between two directions | Direction changes too slowly |
| `alpha_deg` | Too much CPU usage | Angular resolution too coarse |

---

## Troubleshooting

### "No MAVROS connection" in mission_manager
- Check SITL is running: `ps aux | grep ArduCopter`
- Check MAVROS fcu_url matches SITL output port: `udp://:14550`
- MAVROS heartbeat: `ros2 topic echo /mavros/state`

### Drone does not take off
- Check `/mavros/state` shows `armed=True` and `mode=GUIDED`
- SITL may be paused — press Enter in the MAVProxy terminal

### Gazebo world is empty / drone not spawned
- Check `GAZEBO_MODEL_PATH` includes the repo's models directory
- Check `GAZEBO_PLUGIN_PATH` includes the ardupilot_gazebo build dir
- Try spawning manually: `ros2 run gazebo_ros spawn_entity.py --help`

### ArUco detection not working
- Verify the camera topic is publishing: `ros2 topic hz /camera/down/image_raw`
- The landing pad model uses simple geometry (no real texture). For proper
  ArUco detection in simulation, generate and apply a texture:
  ```python
  import cv2, cv2.aruco as aruco
  d = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
  img = aruco.generateImageMarker(d, 0, 512)
  cv2.imwrite('simulation/gazebo/models/landing_pad/materials/textures/aruco_0.png', img)
  ```
  Then update the landing pad SDF to reference this texture.

### High CPU usage
- Reduce Gazebo real-time factor in world file: `<real_time_factor>0.5</real_time_factor>`
- Reduce LiDAR update rate in drone SDF from 10 Hz to 5 Hz
- Reduce camera resolution to 320×240

---

## Docker Alternative

If you prefer not to install everything locally:
```bash
# Experimental — full ROS 2 + Gazebo + MAVROS container
docker build -f docker/Dockerfile.sim -t drone-sim .
docker run --rm -it \
  --env DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --network host \
  drone-sim
```
See `docker/Dockerfile.sim` (to be created in Phase 2) for details.
