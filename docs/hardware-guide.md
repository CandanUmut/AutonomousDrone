# Hardware Guide — Autonomous Delivery Drone

Answers to open design questions with honest tradeoff analysis.

---

## 1. Hot-Swap Battery vs Full Recharge Station

**Verdict: Hot-swap is the right choice for this use case, and it IS realistic.**

### Why hot-swap wins

| Metric | Hot-swap | Recharge-in-place |
|---|---|---|
| Turnaround time | 3–5 min | 45–75 min |
| Station cost | ~$200 (swap mechanism) | ~$150 (just charger) |
| Mechanical complexity | Medium | Low |
| Reliability risk | Connector wear, misalignment | None |
| Throughput | Multiple hops/day possible | One hop every ~1.5 hr |

For a medicine delivery use case, turnaround time matters. A diabetic patient
cannot wait 75 minutes for the insulin drone to recharge.

### What makes it realistic

- **XT90-S antispark connectors**: Rated 90 A continuous, 500+ mate cycles.
  Budget $15 for 10 pairs; replace every 200 swaps.
- **Precision landing**: ArUco marker + downward camera achieves ≤5 cm
  repeatability. The swap mechanism dock only needs ±10 cm tolerance.
- **Servo latch**: A single MG996R servo (10 kg·cm) is more than enough to
  hold and release a 680 g battery sled.
- **Arduino Nano station controller**: $8, simple serial protocol with the
  companion computer.

### What to watch out for

- **Connector orientation**: The battery sled must be physically keyed (e.g.,
  asymmetric notch) to prevent reverse insertion. XT90 is not polarised
  mechanically.
- **Spark on hot-connect**: Always use XT90-S (S = antispark built in) or add
  a 10 Ω pre-charge resistor in parallel.
- **Thermal management**: Charge LiPo packs at ≤1C in ambient temperatures
  above 30°C to avoid cell damage.

---

## 2. LTE/4G vs RF Telemetry

**Verdict: Use both. RF is primary; LTE is fallback.**

### RF (SiK 915 MHz) — Primary

- **Latency**: <50 ms — suitable for real-time MAVLink
- **Range**: 2–5 km LOS at 500 mW
- **Cost**: ~$30 for a pair
- **Interference**: Rare in 915 MHz ISM band for most deployments
- **Works when**: You are within visual range or in a low-population RF environment

### LTE/4G — Fallback

- **Latency**: 80–200 ms — acceptable for telemetry, not ideal for control
- **Range**: Wherever there is cell coverage (most urban delivery areas)
- **Cost**: ~$60 module + $10–20/month SIM
- **Security**: **MUST** use VPN (WireGuard or ZeroTier). Raw MAVLink over
  public internet is a security risk — anyone can send commands.
- **Works when**: RF is blocked (urban canyon, long range) or as backup

### Recommended setup

```
Primary:   SiK 915 MHz radio  →  QGC on laptop for monitoring
Fallback:  LTE + WireGuard VPN → MAVLink forwarded over VPN
Trigger:   MAVROS publishes link quality; companion auto-switches on RF loss
```

---

## 3. FAA Part 107 and Regulatory Considerations

**Read this before any outdoor flight, even a tethered test.**

### What applies to you

If you fly in the US:
- **Part 107** applies to UAS operations (drone + companion software = UAS)
- You need a **Part 107 Remote Pilot Certificate** for commercial ops
  (delivering medicine = commercial even if unpaid)
- Maximum altitude: **400 ft AGL** (unless authorised via LAANC/DroneZone)
- **Visual line of sight (VLOS)** required unless you have a waiver
- **Prohibited areas**: No-fly zones within 5 NM of airports, TFRs, restricted
  airspace. Check the B4UFLY app before every flight.
- **Beyond Visual Line of Sight (BVLOS)**: Requires a Part 107 waiver from the
  FAA — typically takes 6–18 months and requires extensive safety documentation.

For medicine delivery at scale, you will eventually need a BVLOS waiver.
Start collecting safety data now (logs, incident reports, test results) — the
FAA uses this data to evaluate waiver applications.

### Immediate steps (before first outdoor test)

1. Register the drone at registermyuas.faa.gov (required for drones >0.55 lbs)
2. Mark the drone with the FAA registration number
3. Do NOT fly over people or moving vehicles without a waiver
4. File a LAANC authorisation for any airspace within 5 NM of an airport
5. Keep all flight logs — they are your safety evidence

### EU/UK (EASA/CAA)

- Category A1/A2/A3 depends on drone weight and operation type
- Medicine delivery likely falls in **A2** (near people) or **A3** (remote)
- Operators must register at national aviation authority
- For BVLOS or over-populated areas: **Specific Category** with PDRA or STS
- See `compliance/eu-uk/` for links to national authority portals

---

## 4. GPS-Denied Environments

**Under trees and near buildings, GPS degrades. Here is the mitigation stack:**

### Problem severity

| Environment | GPS quality | Mitigation needed |
|---|---|---|
| Open field | Excellent | None |
| Suburban (some trees/buildings) | Good | Better GPS module |
| Urban canyon | Degraded (multipath) | Optical flow + RTK |
| Under dense canopy | Poor/unreliable | VIO or pre-mapped route |
| Indoor | None | Full SLAM or laser-based |

For our target (suburban medicine delivery with planned routes), GPS is
adequate with the right module and antenna placement.

### Mitigation stack (low to high cost)

**Level 1 — Better GPS (~$50)**
Upgrade from M8N to **u-blox M9N** or **Here3**. M9N uses multi-constellation
(GPS + GLONASS + Galileo + BeiDou) and L1+L2 signals, which significantly
reduces multipath.

**Level 2 — Antenna placement (~$0)**
Mount the GPS mast ≥15 cm above the top of the frame, away from ESC wiring.
Use a ground plane (small copper disc under the antenna). This alone can
improve positional accuracy by 30–50% in urban areas.

**Level 3 — Optical flow sensor (~$30–80)**
A downward optical flow sensor (e.g., PX4FLOW or Cheerson CX-OF) gives
relative velocity measurement that ArduCopter fuses with GPS. During short
GPS outages, the EKF maintains position using optical flow + barometer.
Works well if the drone stays above ~2 m and the ground has texture.

**Level 4 — RTK GPS (~$400–600)**
A Here3 (RTK receiver) + RTK base station gives 2–4 cm position accuracy
even near buildings. The base station can be co-located with the swap station.
RTK loses fix in full canopy but handles urban canyons well.

**Level 5 — VIO (Visual Inertial Odometry) (~software + OAK-D)**
Intel RealSense T265 or OAK-D with VIO algorithms provides relative position
without GPS. Can maintain position for 60–120 s without drift on a good
trajectory. Requires the OAK-D or Jetson Orin NX for real-time inference.

**Recommendation for v1**: M9N + antenna mast + optical flow. Total ~$130.
Handles 95% of suburban delivery routes. Add RTK in Phase 4 if needed.

---

## 5. Minimum Viable Sensor Suite (Very Tight Budget)

If you need to prototype on <$400 total hardware:

| Component | Budget option | Cost | Notes |
|---|---|---|---|
| Flight controller | Matek H743 Mini | $45 | ArduCopter, decent IMU |
| GPS | u-blox M8N clone | $20 | Adequate for open areas |
| Camera (ArUco) | Raspberry Pi Camera v2 | $25 | 8 MP, good for detection |
| Distance sensor | TF-Luna | $25 | Down-facing only, no 360° |
| Onboard computer | Raspberry Pi Zero 2W | $15 | Very constrained — no ROS 2 |
| Telemetry | SiK 100 mW | $20 | 1 km range |
| **Total** | | **~$150** | Sensors only |

**What you give up at this budget:**
- 360° obstacle avoidance (TF-Luna is point-only → can see walls but not
  trees to the side)
- Depth camera for rich environment understanding
- High-compute processing (Pi Zero 2W cannot run ROS 2 well)

**Alternative**: Use Raspberry Pi 5 with just one RPLidar A1 (no stereo
camera). This gives full VFH+ obstacle avoidance for ~$160 in sensors.
It is the minimum viable configuration that supports the full software stack.

---

## 6. Sensor Integration Summary

```
                        ┌────────────────────┐
                        │  Pixhawk 6C Mini   │
                        │  (ArduCopter)      │
                        │                    │
                        │ ✓ IMU (ICM-42688)  │
                        │ ✓ Baro (×2)        │
              ┌─────────┤ ✓ Compass (×1)     ├──────────┐
              │         └────────┬───────────┘          │
              │                  │ UART/SPI              │
              │                  │ MAVLink               │
              │          ┌───────▼────────┐              │
              │          │  Raspberry Pi 5│              │
              │          │  (companion)   │              │
              │          │                │              │
              │          │  ✓ MAVSDK      │              │
              │ USB      │  ✓ ArUco       │ USB          │
              │          │  ✓ ROS 2       │              │
         ┌────▼────┐     │  ✓ VFH+        │    ┌────────▼──┐
         │ RPLidar │     └───┬────────┬───┘    │  OAK-D    │
         │  A1M8   │         │        │        │  Lite     │
         └─────────┘    CSI  │        │ USB    └───────────┘
                        ┌────▼────┐   │
                        │ Pi Cam  │   │ UART
                        │  v3     │   │
                        │ (down)  │  ┌▼──────┐
                        └─────────┘  │u-blox │
                                     │  M9N  │
                                     └───────┘
```

Flight controller ↔ companion computer: **UART (MAVLink v2)** at 921600 baud,
connected to `/dev/ttyAMA0` on the Pi 5. Do NOT use USB for FC-companion link
— USB latency is too variable for telemetry.
