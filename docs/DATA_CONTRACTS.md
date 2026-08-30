# Data contracts

The Pydantic models in `backend/app/domain/models.py` define architectural contracts, not generated observations. Nullable later-stage values remain absent until their owner subsystem is implemented.

## Provenance

Every raw sample and sensor frame carries `DataProvenance`:

- `SIMULATED` — produced by an explicit digital-twin source;
- `HARDWARE` — acquired from a physical sensor source.

The current prototype advertises `SIMULATED` because the Digital Patient session is synthetic. The BIS digital twin still reports `NOT_IMPLEMENTED`. No UI copy may represent simulated values as measured patient physiology.

## Time and determinism

`wall_clock_time` is real elapsed calendar time. `simulated_time` is time inside a future accelerated scenario. They must never be silently interchanged. Raw contracts allow `simulated_time` to be absent for hardware observations.

The operational `SimulationSnapshot` contains:

- `simulation_id` for run identity;
- a `SyntheticPatient` whose `synthetic` field can only be `true`;
- `seed` for repeatability;
- both timestamps;
- a bounded positive `speed_multiplier`;
- `data_provenance = SIMULATED`; and
- a lifecycle value.

`SimulationLifecycle` is one of `UNINITIALIZED`, `READY`, `RUNNING`, or `PAUSED`. The `SimulationClockEvent` WebSocket contract carries only simulation identity, lifecycle, timestamps, and speed. It contains no physiological measurements.

All timestamps are timezone-aware. The system uses UTC for transport and monotonic elapsed time internally. Manual-step input is explicit simulated seconds, is positive, is capped at one simulated year per operation, and is only valid while `READY` or `PAUSED`.

The seed identifies deterministic random state, not generated patient physiology. Reset preserves it. Future stochastic modules must request a namespaced seed from the simulation RNG owner so identical seed/start/input sequences can be reproduced without relying on process-global randomness.

## Unit conventions

Units are encoded in field names and follow SI conventions unless explicitly stated:

| Quantity | Contract field / unit |
| --- | --- |
| Frequency | `frequency_hz` / hertz |
| Resistance | `resistance_ohm` / ohms |
| Reactance | `reactance_ohm` / ohms |
| Impedance magnitude | `magnitude_ohm` / ohms |
| Phase | `phase_deg` / degrees |
| Temperature | `temperature_c` / degrees Celsius |
| Linear acceleration | `*_m_s2` / metres per second squared |
| Angular velocity | `*_rad_s` / radians per second |

Frequency must be positive, magnitude non-negative and phase within -180 to 180 degrees. Impedance magnitude must agree with resistance and reactance within a small numerical tolerance. Contact-quality and future normalized anomaly values, when present, use a closed 0–1 range. A field with an unknown unit must not be added as an ambiguous number.

## Bilateral bioimpedance contracts

`ColeModelParameters` defines the synthetic model parameters `r_zero_ohm`, `r_infinity_ohm`, `tau_seconds`, and `beta`. Validation enforces `R0 > R∞ > 0`, `tau > 0`, and `0 < beta ≤ 1`. These are prototype model parameters, not clinical reference values or direct fluid-volume measurements.

`BioimpedanceFrequencyPoint` contains the complete, unit-explicit complex response at one frequency:

- `frequency_hz`
- `resistance_ohm`
- `reactance_ohm`
- `magnitude_ohm`
- `phase_deg`

`BioimpedanceSweep` is one arm's raw source output. `BilateralBioimpedanceSweep` combines exactly aligned left/right sweeps with a shared `pair_id`, `sweep_index`, `simulation_id`, `wall_clock_time`, and `simulated_time`. Arm frequency lists, timestamps, and provenance must match.

All Phase 2 acquisitions have `provenance = SIMULATED`, `source = DIGITAL_TWIN`, and `qualification = RAW_UNQUALIFIED`. They must not contain acceptance/quality flags, diagnoses, risk values, ADI, or ML scores.

The optional bounded noise layer only alters the complex R/X components. Magnitude and phase are calculated from the resulting complex number, preserving internal consistency. Namespaced seeds based on arm and sweep index make repeated output reproducible after reset without reading global random state.

## Virtual wearable sensor contracts

`WearableSensorWindow` is one synchronized bilateral short acquisition. It contains `window_id`, `window_index`, `anchor_simulated_time`, `anchor_wall_clock_time`, `duration_seconds`, provenance/source/qualification, engineering condition inputs, and `left`/`right` `BandSensorWindow` objects. The anchors describe the longitudinal session; they are not sample time.

`BandSensorWindow` stores modality sample rates and three raw sequences: `IMUSample` (local time, acceleration in `m_s2`, angular velocity in `rad_s`, coherent roll/pitch/yaw in degrees), `TemperatureSample` (local time and skin `temperature_c`), and `ContactSample` (local time and `contact_impedance_ohm`). Local timestamps run from 0 to the configured duration and never advance the global simulation clock. `RAW_UNQUALIFIED` only marks the raw stage; it is not an acceptance, rejection, or quality score.

## Data-stage separation

| Stage | Examples | Owner |
| --- | --- | --- |
| RAW | BIS sweeps, IMU, temperature, contact samples | Acquisition source |
| PROCESSED | Filtered signals and feature vectors | Signal-processing subsystem |
| INFERENCE | Model version and anomaly score | ML subsystem |
| TEMPORAL | Persistence assessment and explanation | Temporal subsystem |
| DECISION | Differential index, surveillance state, explanation | Decision subsystem |

The types are separate so raw observations cannot be mistaken for derived results. `MeasurementQualityAssessment`, `ProcessedFeatureVector`, `MLInferenceResult`, `TemporalAssessment`, `ConfounderAssessment`, and `DecisionSnapshot` all include an explicit subsystem status. Their later-stage values are nullable; Phase 1 never fills those values merely to satisfy a schema.

## Validation behavior

Contracts reject unknown fields, invalid enum members, impossible normalized-score ranges, non-positive frequencies and speed multipliers, invalid phase ranges, and inconsistent impedance magnitude. These checks enforce structural integrity only and are not medical validation.
