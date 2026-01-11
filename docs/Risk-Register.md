# Risk Register (Top 15)

| ID | Risk | Likelihood | Impact | Mitigations | Owner | Validation Test |
|---|---|---|---|---|---|---|
| R1 | Autopilot instability | Med | High | Conservative tuning, simulation validation | SW | SITL stability tests |
| R2 | Power system failure | Med | High | Redundant checks, battery health monitoring | HW | Bench power tests |
| R3 | Lost link | Med | High | RTH + geofence + failsafe | Both | RF loss test |
| R4 | GPS degradation | Low | High | Multi-GNSS/RTK, fallback behavior | HW | GPS shadow tests |
| R5 | Sensor drift | Med | Med | Calibration routines | HW | Calibration validation |
| R6 | Airframe structural failure | Low | High | Load testing, conservative limits | HW | Static load test |
| R7 | Propulsion failure | Low | High | Redundant inspection, ESC monitoring | HW | Motor endurance test |
| R8 | Software regression | Med | Med | CI checks, test suite | SW | Regression test run |
| R9 | Ground station error | Med | Med | SOPs, training | Both | Checklist adherence |
| R10 | Regulatory non-compliance | Med | High | Compliance checklist | Both | Preflight compliance review |
| R11 | Supply chain delay | Med | Med | Alternate suppliers | HW | BOM review |
| R12 | Weather/wind exceedance | Med | High | Go/no-go gates | Both | Weather constraints |
| R13 | Data loss | Low | Med | Redundant logging | SW | Log integrity check |
| R14 | Payload integration failure | Med | Med | Interface specs | HW | Payload bench test |
| R15 | Mission plan error | Med | High | Mission review workflow | SW | Mission validation |
