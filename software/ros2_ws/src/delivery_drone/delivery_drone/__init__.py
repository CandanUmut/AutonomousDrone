"""
delivery_drone — ROS 2 autonomy stack for autonomous medicine delivery.

Nodes:
    mission_manager     Full delivery state machine (IDLE → COMPLETE)
    obstacle_avoidance  VFH+ real-time obstacle avoidance from 2D LiDAR
    battery_monitor     Battery telemetry + hot-swap station logic
    precision_landing   ArUco marker detection for precision landing
    payload_manager     Payload bay release control
"""
