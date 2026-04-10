# Bill of Materials — Autonomous Delivery Drone

Prices are approximate USD as of early 2025. Budget and performance tiers are
both listed. Links are illustrative — verify stock and pricing before ordering.

---

## 1. Airframe

| Component | Budget Option | Perf Option | Notes |
|---|---|---|---|
| Frame | F450 clone (generic) · **$15–25** | Tarot 650 Sport · **$80** | F450 is ubiquitous and crash-repairable; 650mm if you need >1 kg payload |
| Landing gear extension | Generic 10 mm standoffs · **$5** | Tarot retractable · **$35** | Higher clearance for payload bay and swap station alignment |
| Payload bay | 3D-printed PLA · **$3 filament** | CNC alu tray · **$20** | 200×150×80 mm fits standard medicine transport box |

**Recommendation**: Start with the F450 clone for simulation/bench. Move to
Tarot 650 if payload exceeds 700 g or flight time needs exceed 18 min.

---

## 2. Propulsion

### Motors (× 4)
| Option | KV | Price each | Notes |
|---|---|---|---|
| SunnySky X2212-980KV | 980 | **$18** | Best budget efficiency; runs 9–10" props on 4S |
| T-Motor MN2213-920KV | 920 | **$28** | Better build quality; smoother telemetry |
| T-Motor MN3508-700KV | 700 | **$45** | **Recommended** for 6S + 1 kg payload |

**6S + T-Motor MN3508** is the recommended combination: higher efficiency at
cruise (55–60% throttle), less heat, longer motor life.

### ESCs (× 4)
| Option | Current | Price each | Notes |
|---|---|---|---|
| Hobbywing XRotor 20A | 20 A | **$18** | BLHeli_S, good for up to 650 g total per arm |
| Hobbywing XRotor 40A | 40 A | **$25** | **Recommended** for 6S + MN3508 |
| T-Motor F45A | 45 A | **$32** | Bidirectional DSHOT, FOC option |

### Propellers
| Option | Size | Price | Notes |
|---|---|---|---|
| Generic carbon 9045 (2-blade) | 9×4.5" | **$8 set of 4** | Good for 4S budget build |
| T-Motor P15×5 (3-blade) | 15×5" | **$22 set of 4** | **Recommended** for 6S MN3508; better thrust/noise |
| APC 10×4.7 (3-blade) | 10×4.7" | **$12 set of 4** | Good middle ground |

**Estimated thrust** (6S + MN3508 + 15" prop): ~800 g per motor × 4 = 3.2 kg
max thrust. With 2.5 kg all-up weight, that's a 1.28 thrust-to-weight ratio —
acceptable for a delivery drone (aim for ≥1.5 for reserve).

> **Safety flag**: Always verify motor/prop/ESC compatibility before first
> power-on. An undersized ESC will overheat and fail in flight.

---

## 3. Power System

### Battery (need 2–3 for hot-swap rotation)
| Option | Capacity | C-rating | Weight | Price | Notes |
|---|---|---|---|---|---|
| CNHL 4S 6000mAh 60C | 4S | 60C | 460 g | **$45** | Budget option |
| Tattu 6S 6000mAh 25C | 6S | 25C | 680 g | **$75** | **Recommended** |
| Tattu Plus 6S 10000mAh | 6S | 25C | 1050 g | **$130** | Extended range; heavy |

**Recommended**: 6S 6000 mAh × 3 batteries (~$225 total) for a hot-swap pool.
Estimated flight time per charge: **16–20 min** at ~60% load with 1 kg payload.

**Hot-swap connector**: XT90 antispark (not XT60 — XT60 is marginal for 6S).
The antispark variant prevents the spark on connection that damages contacts
over time.

### BMS / Power Distribution Board
| Component | Option | Price | Notes |
|---|---|---|---|
| PDB | Matek FCHUB-6S | **$18** | Integrated BEC, current sensor, 6S-capable |
| Voltage/current sensor | Matek FCHUB built-in | included | Outputs to flight controller |
| BEC (5 V for FC/RPi) | Pololu D36V28F5 | **$15** | 5 A, clean regulation for compute |

### Solar Charging Station
| Component | Model | Price | Notes |
|---|---|---|---|
| Solar panel | Renogy 200W Rigid | **$85** | 18 V Voc; 2–3 of these for faster charge |
| MPPT controller | Victron SmartSolar 75/15 | **$75** | Bluetooth monitoring, 12/24 V bus |
| Charge station battery | LiFePO4 12V 100Ah | **$120** | Buffer to charge LiPo packs from |
| LiPo balance charger | iCharger 308 Duo | **$160** | Charges two 6S packs simultaneously |
| Relay/contactor for swap | Tyco EV200 | **$15** | Isolates battery during swap |

**Charge time** (6000 mAh 6S at 5 A): ~72 min per pack. With 200 W solar
(~10–11 A at 18 V) and a buffer battery, you can charge packs faster (up to 3C
= 18 A for quality LiPo), but heat becomes a concern above 2C outdoor charging.

---

## 4. Flight Controller

| Option | Price | Notes |
|---|---|---|
| Holybro Pixhawk 4 Mini | **$100** | Compact, good IMU (ICM-20689), well-supported |
| Holybro Pixhawk 6C Mini | **$175** | **Recommended** — newer IMU (ICM-42688-P), better noise floor |
| Cube Orange+ | **$260** | Best IMU redundancy; overkill for v1 but future-proof |

**Recommendation**: Pixhawk 6C Mini with ArduCopter firmware. The ICM-42688-P
IMU has better vibration rejection than the 20689, which matters for a
propeller-vibration-prone delivery frame.

Integrated on Pixhawk 6C Mini: IMU (×2), barometer (×2), compass (×1).
External compass required if you install it away from power noise.

---

## 5. Onboard Computer (Companion)

| Option | Price | RAM | GPU/NPU | Notes |
|---|---|---|---|---|
| Raspberry Pi 5 (4 GB) | **$60** | 4 GB | None | **Minimum viable**; good for MAVSDK + basic vision |
| Raspberry Pi 5 (8 GB) | **$80** | 8 GB | None | Recommended for ROS 2 + OpenCV ArUco |
| Orange Pi 5 (8 GB) | **$75** | 8 GB | NPU 6 TOPS | Cost competitive with RPi 5; RK3588 |
| Jetson Orin NX 8 GB | **$500** | 8 GB | 70 TOPS | Overkill for delivery; use for depth/ML inference |

**Recommendation**: Raspberry Pi 5 8 GB. It runs ROS 2 Humble natively,
handles ArUco detection at 30 fps on a Pi camera, and fits within a realistic
drone weight budget. If you add deep-learning-based obstacle detection later,
migrate to Jetson Orin NX.

---

## 6. Sensors

### GPS
| Option | Price | Notes |
|---|---|---|
| u-blox M8N (generic) | **$20–30** | Adequate; M8N struggles in urban canyons |
| Holybro M9N | **$50** | **Recommended** — better multi-constellation (GPS+GLONASS+Galileo) |
| Here3 (RTK-capable) | **$130** | Use if you need <10 cm landing accuracy without ArUco |

### LiDAR
| Option | Range | FOV | Price | Notes |
|---|---|---|---|---|
| TF-Luna | 8 m | Point | **$25** | Minimum viable — only down-facing ranging |
| RPLidar A1M8 | 12 m | 360° 2D | **$99** | **Recommended** — 360° scan for VFH+ avoidance |
| RPLidar A2M12 | 18 m | 360° 2D | **$179** | Better range; worth it for >5 m/s cruise |
| Garmin Lidar-Lite v3 | 40 m | Point | **$150** | Good for precision altitude hold only |

**Recommendation**: RPLidar A1M8 for obstacle avoidance + TF-Luna pointing
downward for precision landing altitude. Total: ~$124.

### Camera
| Option | Type | Price | Notes |
|---|---|---|---|
| Pi Camera Module 3 | Monocular | **$25** | Adequate for ArUco detection at <3 m |
| OAK-D Lite | Stereo + depth | **$149** | **Recommended** — depth up to 10 m, onboard AI |
| Intel RealSense D435i | Stereo + IMU | **$200** | More mature SDK, larger; heavier than OAK-D |

**Recommendation**: Pi Camera Module 3 (downward, for ArUco) + OAK-D Lite
(forward, for obstacle detection). The OAK-D Lite provides depth without
needing LiDAR directly in front — LiDAR handles 360° low-reflectivity
obstacles, camera handles the forward arc more richly.

### IMU
Built into Pixhawk 6C Mini (ICM-42688-P). No separate IMU needed unless you
are running your own EKF on the companion computer.

### Barometer / Compass
- Barometer: Built into Pixhawk (×2 on 6C Mini). No separate unit needed.
- Compass: Built into M9N GPS module. Recommended to mount GPS on a mast
  ≥10 cm above the PDB/ESCs to reduce magnetic interference.

---

## 7. Communication

### RF Telemetry (Primary)
| Option | Frequency | Range | Price | Notes |
|---|---|---|---|---|
| SiK Holybro 500mW | 915 MHz | ~2 km LOS | **$30** | Standard ArduPilot telemetry |
| Herelink (video+telemetry) | 2.4 GHz | ~20 km LOS | **$700** | Overkill for v1 |

### LTE/4G (Fallback)
| Option | Price | Notes |
|---|---|---|
| Sixfab Raspberry Pi 4G/LTE HAT | **$60** + SIM | Runs on RPi 5; uses ppp/nmea for routing |
| Holybro LTE module | **$80** | MAVLink-over-LTE; easier to configure |

**Recommendation**: SiK 915 MHz radio for primary telemetry + Sixfab 4G for
LTE fallback. Use ZeroTier or WireGuard VPN to secure the LTE MAVLink tunnel.

---

## 8. Hot-Swap Mechanism

The battery swap station requires:
- **Landing precision**: ≤5 cm, achieved with ArUco marker + Pi Camera
- **Connector**: XT90-S antispark, rated for 90 A continuous, robust to >500
  mate/unmate cycles
- **Swap mechanism**: Servo-actuated latch that holds and releases a
  standardized battery sled

| Component | Price | Notes |
|---|---|---|
| Servo (for latch) | **$12** (MG996R) | 10 kg·cm is sufficient |
| Battery sled (3D printed) | **$5 filament** | Design to match frame battery bay |
| XT90-S connector (×10) | **$15** | Replace every 200 cycles |
| Limit switches (×2) | **$5** | Detect battery seated/removed |
| Arduino Nano (station controller) | **$8** | Controls servo + reads limit switches |

Total swap mechanism hardware: **~$45**

---

## 9. Total Cost Summary

### Budget Build (~$700–900)
F450 clone + SunnySky motors + Pixhawk 4 Mini + RPi 5 4GB + RPLidar A1 +
Pi Camera × 2 + M8N GPS + 6S LiPo × 2

### Recommended Build (~$1,200–1,500)
Tarot 650 + T-Motor MN3508 + Pixhawk 6C Mini + RPi 5 8GB + RPLidar A1 +
OAK-D Lite + Pi Camera (down) + M9N GPS + 6S LiPo × 3 + SiK telemetry +
solar station (basic)

### Full Build with LTE + Better Compute (~$2,000–2,500)
Above + Jetson Orin NX + 4G LTE + RTK GPS + RPLidar A2 + RealSense D435

---

## 10. Open Questions / Risks

- **Battery standardization**: Define a fixed battery form factor early. Once
  the swap sled is designed and printed, changing battery dimensions is costly.
- **XT90 wear**: Track mate/unmate cycles. Replace connectors at 200 cycles or
  when contact resistance increases (measure with a clamp meter).
- **RPi 5 current draw**: Peak draw is ~5 W. Use a dedicated BEC (not FC BEC)
  to avoid noise coupling into IMU.
- **Weight budget**: Confirm all-up weight before first flight.
  Target: frame (500 g) + motors (4×140 g) + battery (680 g) + FC (80 g) +
  RPi (50 g) + sensors (200 g) + payload (500 g) = **~2.57 kg**.
  MN3508 max thrust ~3.2 kg total — marginal. Consider 15" props (700 KV) or
  upgrade to 650 mm frame for comfortable 1.5× thrust-to-weight.
