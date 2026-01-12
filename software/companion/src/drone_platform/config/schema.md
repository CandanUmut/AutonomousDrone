# Configuration Schema

Configuration files are YAML. All numeric values use SI units unless noted.

## Root

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `connection` | object | ✅ | MAVSDK connection details. |
| `mission` | object | ✅ | Mission parameters and waypoints. |
| `geofence` | object | ✅ | Geofence definition for sanity checks. |
| `safety` | object | ✅ | Safety gating and mode selection. |
| `logging` | object | ✅ | Structured logging configuration. |

## connection

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `system_address` | string | ✅ | MAVSDK connection string (ex: `udp://:14540`). |

## mission

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `takeoff_alt_m` | number | ✅ | Takeoff altitude in meters. |
| `rtl_alt_m` | number | ✅ | Return-to-launch altitude in meters. |
| `waypoints` | array | ✅ | Ordered list of waypoints to visit. |

### mission.waypoints[]

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `lat` | number | ✅ | Latitude in degrees. |
| `lon` | number | ✅ | Longitude in degrees. |
| `alt_m` | number | ✅ | Altitude in meters. |

## geofence

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `center_lat` | number | ✅ | Geofence center latitude. |
| `center_lon` | number | ✅ | Geofence center longitude. |
| `radius_m` | number | ✅ | Radius in meters. |
| `min_alt_m` | number | ✅ | Minimum altitude. |
| `max_alt_m` | number | ✅ | Maximum altitude. |

## safety

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `mode` | string | ✅ | `sim` or `hardware`. Defaults to `sim`. |
| `allow_hardware` | boolean | ✅ | Must be true to run in hardware mode. |
| `sim_only_banner` | boolean | ✅ | Show SIM-only banner before mission start. |

## logging

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `level` | string | ✅ | Logging level (`INFO`, `DEBUG`, etc). |
| `log_dir` | string | ✅ | Directory for log output. |
| `json` | boolean | ✅ | Enable JSON structured logs. |
