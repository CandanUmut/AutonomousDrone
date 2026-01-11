# System Architecture

## Hardware block diagram (ASCII)
```
[Airframe]
   |--[Propulsion: motor/ESC/prop]
   |--[Power: battery, BMS]
   |--[Autopilot]
   |--[Sensors: IMU, GPS/RTK, airspeed, baro]
   |--[Companion Compute]
   |--[Comms: telemetry + RC failsafe]
   |--[Payload: delivery/inspection module]
```

## Software block diagram (ASCII)
```
[Mission Planner] -> [Telemetry Link] -> [Autopilot (PX4/ArduPilot)]
                               |-> [Companion Compute]
                                   |-> [Mission Manager]
                                   |-> [Perception/Monitoring]
                                   |-> [Logging + Data Mgmt]
```

## Core subsystems
- Airframe
- Propulsion
- Power and energy
- Autopilot (PX4/ArduPilot)
- Companion compute (ROS2 optional)
- Sensors
- Communications
- Payload

## Interfaces
- **MAVLink** between autopilot and companion compute.
- Telemetry and logging links for ground control.
- Firmware update process with versioned releases.
