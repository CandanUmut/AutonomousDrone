from drone_platform.autonomy.geofence import Geofence
from drone_platform.common.types import GeofenceConfig


def test_geofence_contains() -> None:
    config = GeofenceConfig(
        center_lat=47.0,
        center_lon=8.0,
        radius_m=100.0,
        min_alt_m=0.0,
        max_alt_m=120.0,
    )
    geofence = Geofence.from_config(config)

    assert geofence.contains(47.0, 8.0, 10.0)
    assert not geofence.contains(47.01, 8.0, 10.0)
