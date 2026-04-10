"""
simulation.launch.py — Full simulation stack launch file.

Starts:
  1. Gazebo with the urban delivery world
  2. ArduCopter SITL (via subprocess, see docs/simulation-guide.md)
  3. MAVROS (MAVLink ↔ ROS 2 bridge)
  4. Robot State Publisher (URDF/SDF TF tree)
  5. All delivery_drone autonomy nodes

Usage:
    ros2 launch delivery_drone simulation.launch.py

Optional arguments:
    world_file:=<path>          Override world SDF path
    drone_x:=0.0               Drone spawn X (ENU metres)
    drone_y:=0.0               Drone spawn Y
    drone_z:=0.3               Drone spawn Z (above ground)
    delivery_x:=80.0           Delivery target X
    delivery_y:=5.0            Delivery target Y
    mavros_url:=udp://:14550   MAVROS FCU connection URL

Note: ArduCopter SITL must be started separately before this launch.
      Run:  ./scripts/sim_ardupilot.sh
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os


def generate_launch_description() -> LaunchDescription:
    pkg_share = FindPackageShare("delivery_drone")

    # ------------------------------------------------------------------ Arguments
    world_arg = DeclareLaunchArgument(
        "world_file",
        default_value=os.path.join(
            os.path.dirname(__file__),
            "../../../../simulation/gazebo/worlds/delivery_urban.world",
        ),
        description="Path to Gazebo world file",
    )
    drone_x_arg = DeclareLaunchArgument("drone_x", default_value="0.0")
    drone_y_arg = DeclareLaunchArgument("drone_y", default_value="0.0")
    drone_z_arg = DeclareLaunchArgument("drone_z", default_value="0.3")
    delivery_x_arg = DeclareLaunchArgument("delivery_x", default_value="80.0")
    delivery_y_arg = DeclareLaunchArgument("delivery_y", default_value="5.0")
    mavros_url_arg = DeclareLaunchArgument(
        "mavros_url", default_value="udp://:14550"
    )
    launch_gazebo_arg = DeclareLaunchArgument(
        "launch_gazebo", default_value="true", description="Launch Gazebo simulator"
    )

    # ------------------------------------------------------------------ Gazebo
    gazebo = ExecuteProcess(
        cmd=[
            "gazebo",
            "--verbose",
            LaunchConfiguration("world_file"),
            "-s", "libgazebo_ros_factory.so",
            "-s", "libgazebo_ros_init.so",
        ],
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_gazebo")),
    )

    # Spawn drone model after Gazebo starts
    spawn_drone = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "ros2", "run", "gazebo_ros", "spawn_entity.py",
                    "-file", os.path.join(
                        os.path.dirname(__file__),
                        "../../../../simulation/gazebo/models/delivery_drone/model.sdf",
                    ),
                    "-entity", "delivery_drone",
                    "-x", LaunchConfiguration("drone_x"),
                    "-y", LaunchConfiguration("drone_y"),
                    "-z", LaunchConfiguration("drone_z"),
                ],
                output="screen",
            )
        ],
    )

    # ------------------------------------------------------------------ MAVROS
    mavros_node = Node(
        package="mavros",
        executable="mavros_node",
        name="mavros",
        output="screen",
        parameters=[
            {"fcu_url": LaunchConfiguration("mavros_url")},
            {"gcs_url": ""},
            {"target_system_id": 1},
            {"target_component_id": 1},
            {"fcu_protocol": "v2.0"},
            PathJoinSubstitution([pkg_share, "config", "drone_params.yaml"]),
        ],
    )

    # ------------------------------------------------------------------ Autonomy nodes
    mission_manager = Node(
        package="delivery_drone",
        executable="mission_manager",
        name="mission_manager_node",
        output="screen",
        parameters=[
            PathJoinSubstitution([pkg_share, "config", "drone_params.yaml"]),
            {
                "delivery_x": LaunchConfiguration("delivery_x"),
                "delivery_y": LaunchConfiguration("delivery_y"),
            },
        ],
    )

    obstacle_avoidance = Node(
        package="delivery_drone",
        executable="obstacle_avoidance",
        name="obstacle_avoidance_node",
        output="screen",
        parameters=[PathJoinSubstitution([pkg_share, "config", "drone_params.yaml"])],
        remappings=[
            ("/scan", "/drone/scan"),
        ],
    )

    battery_monitor = Node(
        package="delivery_drone",
        executable="battery_monitor",
        name="battery_monitor_node",
        output="screen",
        parameters=[PathJoinSubstitution([pkg_share, "config", "drone_params.yaml"])],
    )

    precision_landing = Node(
        package="delivery_drone",
        executable="precision_landing",
        name="precision_landing_node",
        output="screen",
        parameters=[PathJoinSubstitution([pkg_share, "config", "drone_params.yaml"])],
        remappings=[
            ("/camera/down/image_raw", "/drone/camera/down/image_raw"),
            ("/camera/down/camera_info", "/drone/camera/down/camera_info"),
        ],
    )

    payload_manager = Node(
        package="delivery_drone",
        executable="payload_manager",
        name="payload_manager_node",
        output="screen",
        parameters=[
            PathJoinSubstitution([pkg_share, "config", "drone_params.yaml"]),
            {"simulation_mode": True},
        ],
    )

    # ------------------------------------------------------------------ RViz2 (optional)
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", PathJoinSubstitution([pkg_share, "config", "delivery_drone.rviz"])],
        output="screen",
    )

    return LaunchDescription([
        # Arguments
        world_arg,
        drone_x_arg,
        drone_y_arg,
        drone_z_arg,
        delivery_x_arg,
        delivery_y_arg,
        mavros_url_arg,
        launch_gazebo_arg,
        # Simulation
        gazebo,
        spawn_drone,
        # ROS nodes (start after MAVROS is ready — TimerAction)
        TimerAction(period=3.0, actions=[mavros_node]),
        TimerAction(period=8.0, actions=[mission_manager]),
        TimerAction(period=8.0, actions=[obstacle_avoidance]),
        TimerAction(period=8.0, actions=[battery_monitor]),
        TimerAction(period=8.0, actions=[precision_landing]),
        TimerAction(period=8.0, actions=[payload_manager]),
    ])
