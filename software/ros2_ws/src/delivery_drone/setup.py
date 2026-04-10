from setuptools import find_packages, setup
import os
from glob import glob

package_name = "delivery_drone"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="AutonomousDrone Project",
    maintainer_email="team@autonomousdrone.local",
    description="ROS 2 autonomy stack for the autonomous delivery drone",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mission_manager = delivery_drone.mission_manager_node:main",
            "obstacle_avoidance = delivery_drone.obstacle_avoidance_node:main",
            "battery_monitor = delivery_drone.battery_monitor_node:main",
            "precision_landing = delivery_drone.precision_landing_node:main",
            "payload_manager = delivery_drone.payload_manager_node:main",
        ],
    },
)
