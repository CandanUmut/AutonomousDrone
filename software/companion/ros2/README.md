# ROS2 (Optional)

ROS2 integration is **off by default** in v2. The lightweight bridge is intended
to republish MAVSDK telemetry and accept mission commands from ROS2 nodes.

## Planned package layout

```
ros2/
  drone_platform_bridge/
    package.xml
    setup.py
    drone_platform_bridge/
      node.py
```

## Intended topics/services (stub)

- `/drone/telemetry/position`
- `/drone/telemetry/battery`
- `/drone/mission/start`
- `/drone/mission/abort`

These are placeholders. Implementation will be added once the core companion
stack is validated in SITL.
