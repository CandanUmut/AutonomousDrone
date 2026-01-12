from drone_platform.config import default_config_path, load_config


def test_load_default_config() -> None:
    path = default_config_path()
    assert path.exists()
    config = load_config(path)
    assert config.safety.mode == "sim"
    assert config.connection.system_address.startswith("udp://")
    assert len(config.mission.waypoints) >= 3
