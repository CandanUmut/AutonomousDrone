# ADR-0005: Multirotor Airframe for Delivery Use Case

## Status

Accepted — **supersedes ADR-0002**

## Context

ADR-0002 selected a fixed-wing airframe with catapult launch and belly landing.
This was reconsidered once the concrete mission profile was defined:

- Last-mile medicine/supply delivery to specific GPS coordinates
- Payload ~500 g–1 kg in a rigid box
- Precision landing at a battery-swap station (repeatably, to within ~20 cm)
- Hot-swap battery system requiring the drone to land on a physical fixture
- Urban/suburban environment with varied terrain, buildings, and trees
- Flight range 2–10 km per hop (within hot-swap infrastructure range)

A fixed-wing airframe is fundamentally incompatible with several of these
requirements:

| Requirement | Fixed-wing | Multirotor |
|---|---|---|
| Hover for delivery confirmation | No | Yes |
| Precision landing on a pad (<30 cm) | Very difficult | Yes (ArUco + vision) |
| Hot-swap station (repeatable docking) | Impractical | Yes |
| Vertical takeoff from confined space | No (needs catapult) | Yes |
| Low-speed maneuvering near obstacles | Dangerous | Yes |
| Short-hop range (2–5 km) | Inefficient | Acceptable |
| Mechanical complexity | High (launch+recovery) | Low |

For 2–10 km hops in an urban/suburban grid served by swap stations, a
multirotor's efficiency penalty is acceptable and is outweighed by operational
simplicity and the ability to hover, precision-land, and dock reliably.

## Decision

Use a **450 mm-class quadrotor** (X-configuration) as the primary airframe.

Specific rationale:

- **450 mm frame**: Proven balance of payload capacity (up to 1.5 kg useful
  payload with 6S power), flight time (~15–20 min), and portability.
- **X-configuration**: Better yaw authority than + config; more aerodynamically
  symmetric for GPS hold and position control.
- **4 rotors**: Simpler than hex/octo; failure of one rotor is unrecoverable
  but the probability is acceptable for low-altitude delivery hops. A hex
  would add ~$100–200 cost and weight.
- **ArduCopter firmware**: More mature than PX4 for waypoint delivery missions,
  better auto-tuning, and wider community support for non-standard payloads.

## Alternatives Considered

### Hexacopter (650 mm class)
- Pro: Single-motor failure survivable, higher payload (up to 3 kg)
- Con: 50% more motors/ESCs, heavier, more expensive, overkill for 500 g payload
- **Rejected**: Overkill for the target payload; adds cost and complexity

### Fixed-wing with VTOL transition (tailsitter or tiltrotor)
- Pro: Efficient cruise for >10 km hops
- Con: Mechanically complex, expensive, impractical for precision landing and
  hot-swap docking, longer development time
- **Rejected**: Complexity vs. benefit ratio is poor at our budget and range

### Fixed-wing with catapult (ADR-0002)
- **Rejected**: Cannot hover, cannot precision-land on a pad, incompatible
  with hot-swap station design, operationally complex

## Consequences

- Hardware requirements documents must be updated for multirotor
- Simulation model switches from fixed-wing SDF to quadrotor SDF
- ArduCopter SITL replaces ArduPlane SITL
- Flight controller tuning profiles are copter-specific
- Future upgrade path to hexacopter is straightforward (same firmware family)
