from __future__ import annotations

import math
from dataclasses import dataclass

from drone_platform.common.types import GeofenceConfig


@dataclass(frozen=True)
class Geofence:
    center_lat: float
    center_lon: float
    radius_m: float
    min_alt_m: float
    max_alt_m: float

    @classmethod
    def from_config(cls, config: GeofenceConfig) -> "Geofence":
        return cls(
            center_lat=config.center_lat,
            center_lon=config.center_lon,
            radius_m=config.radius_m,
            min_alt_m=config.min_alt_m,
            max_alt_m=config.max_alt_m,
        )

    def contains(self, lat: float, lon: float, alt_m: float) -> bool:
        in_radius = self._distance_m(lat, lon) <= self.radius_m
        in_altitude = self.min_alt_m <= alt_m <= self.max_alt_m
        return in_radius and in_altitude

    def _distance_m(self, lat: float, lon: float) -> float:
        earth_radius_m = 6371000.0
        lat1 = math.radians(self.center_lat)
        lon1 = math.radians(self.center_lon)
        lat2 = math.radians(lat)
        lon2 = math.radians(lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return earth_radius_m * c
