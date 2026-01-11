# MVP Requirements

## Candidate MVP concepts
1. **Fixed-wing + launch assist + belly landing (Recommended)**
2. **Tailsitter VTOL**
3. **Hybrid lift + cruise**

### Recommendation
**Fixed-wing with launch assist** is the v1 direction. Rationale: lower complexity, easier airframe build, efficient range/endurance, and manageable safety envelope for a small team. Alignment with research report: CITATION-TODO.

## Minimum requirements (v1)
**Airframe performance goals** (engineering targets; adjust after testing):
- Payload: **1–2 kg** (CITATION-TODO / NEEDS VERIFICATION)
- Range: **10–20 km** (NEEDS VERIFICATION)
- Endurance: **45–75 min** (NEEDS VERIFICATION)
- Cruise speed: **18–25 m/s** (NEEDS VERIFICATION)
- Stall speed target: **< 12 m/s** (NEEDS VERIFICATION)
- Wind tolerance target: **< 8 m/s** (NEEDS VERIFICATION)
- Noise target: **engineering goal only** (NEEDS VERIFICATION)

**Autonomy baseline**
- Waypoint navigation with mission upload
- RTH on lost link
- Geofence enforcement
- Basic landing sequence or controlled descent
- Telemetry logging to onboard storage

**Safety baseline**
- Hardware kill switch
- Preflight checklist compliance
- Flight termination approach (controlled descent; no unsafe behavior)
- Test range constraints and safety perimeter

## Assumptions
- MVP is for controlled testing environments.
- Payloads are non-hazardous.
- Operators remain VLOS for v1.

## Open questions
- Optimal payload integration mechanism for v1.
- Launch assist trade-offs (bungee vs catapult).
- Battery chemistry and energy density assumptions.
