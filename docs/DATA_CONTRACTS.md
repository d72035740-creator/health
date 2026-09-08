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

## Measurement quality contracts

`MeasurementQualityAssessment` records `window_id`, `window_index`, `provenance`, `qualification` (`QUALIFIED` or `REJECTED`), `overall_score`, five 0–100 `QualityDimensionScores`, per-arm `QualityFeatureSummary`, structured `RejectionReason` values, evaluation metadata, and the versioned quality-engine/threshold revision. Scores describe technical acquisition conditions only.

`MeasurementAttempt` contains the sensor window, quality assessment, and nullable `bis_sweep`. The invariant is strict: rejected means `bis_sweep = null`; qualified means a synchronized bilateral BIS sweep exists. `quality-v1` thresholds are prototype engineering thresholds, not clinical cutoffs.

## Processed BIS feature contracts

`ProcessedBioimpedanceFeatures` is a named, versioned (`bis-features-v1`) processed snapshot containing the measurement-attempt and sweep identities, simulated time, provenance, per-frequency bilateral features, left/right spectral features, Cole-fit results, and technical-quality context. Per-frequency signed features include magnitude ratio, natural-log ratio, resistance ratio, reactance difference in ohms, phase difference in degrees, and normalized magnitude difference. Spectral slopes are ordinary least-squares slopes of each arm's magnitude or resistance against `log10(frequency_hz)`.

`ColeFitResult` reports `fit_success`, nullable `r0_ohm`, `rinf_ohm`, `tau_seconds`, `beta`, and complex R/X `complex_rmse_ohm`; it never substitutes zero for unavailable parameters. `to_ml_vector()` has explicit fixed ordering and excludes fit-dependent fields. These transformations are engineering features, not clinical biomarkers or anomaly scores.

## Baseline and scenario contracts

`PersonalizedBaselineSnapshot` records lifecycle (`UNINITIALIZED`, `CALIBRATING`, `READY`), revisions, observation count/span, and robust `BaselineFeatureStatistics` (count, median, MAD, Q1, Q3, IQR, robust scale). `BaselineComparison` returns current value, personal median, robust scale, and signed normalized delta per feature; it is not an anomaly or risk score.

`ScenarioType` values are synthetic engineering presets (`BASELINE_STABLE`, systemic, transient, slow, rapid, and recovery variants). Scenario state exposes type, affected arm, authoritative start/elapsed time, progression severity in [0,1], and `scenario-v1`. Effective physiology remains internal to the digital-twin input boundary; scenario fields do not enter processed features or baseline statistics.

## ML contracts

`MLInputVector` is the fixed, ordered 34-value adapter (`aequor-ml-input-v1`) produced from `ProcessedBioimpedanceFeatures` and normalized with the exact `baseline-v1` median/robust-scale values. Values are clipped before model execution. `MLInferenceResult` records runtime/model revisions, reconstruction MSE, model novelty score, latency, tensor dimensions, artifact size, provenance, and an explicit error when inference is unavailable. It is only populated for qualified attempts with a READY baseline and a loaded, hash-verified INT8 TFLite artifact. The score is model novelty, never disease probability, risk, temporal persistence, or a clinical decision; scenario truth is excluded from both the vector and comparison calculation.

## Data-stage separation

`TemporalObservation` stores only eligible observed ML outputs and authoritative simulated timestamps. `TemporalAssessment` exposes time-aware EWMA, cumulative engineering CUSUM, persistence duration, recent simulated-time slope, and non-clinical temporal evidence state. `ConfounderAssessment` exposes bounded bilateral coherence, unilateral asymmetry, observed dominant side, temperature/technical residual evidence, transient evidence, and deterministic explanation codes. Neither contract contains scenario truth, diagnosis, risk, ADI, or a final surveillance state.

| Stage | Examples | Owner |
| --- | --- | --- |
| RAW | BIS sweeps, IMU, temperature, contact samples | Acquisition source |
| PROCESSED | Filtered signals and feature vectors | Signal-processing subsystem |
| INFERENCE | Model version and anomaly score | ML subsystem |
| TEMPORAL | Persistence assessment and explanation | Temporal subsystem |
| DECISION | Differential index, surveillance state, explanation | Decision subsystem |

The types are separate so raw observations cannot be mistaken for derived results. `MeasurementQualityAssessment`, `ProcessedFeatureVector`, `MLInferenceResult`, `TemporalAssessment`, `ConfounderAssessment`, and `DecisionSnapshot` all include an explicit subsystem status. Their later-stage values are nullable; Phase 1 never fills those values merely to satisfy a schema.

## Validation behavior

## Product view contracts

`PatientViewSnapshot` contains conservative state copy, calibration progress, a dimensionless bilateral presentation metric, recent pattern trend, simple measurement-use language, and a privacy summary. `PatientTrendPoint` is derived from observed personal-baseline comparisons and contains no raw impedance or ML output. `PatientMeasurementSummary` distinguishes qualified and skipped attempts.

`ClinicianViewSnapshot` adds ADI components/modifiers, observed dominant side, selected bilateral and spectral evidence, temporal and confounder summaries, explanations, state history, and compact model provenance. `ClinicianTrendPoint` derives from authoritative runtime history. Neither presentation contract contains scenario type, severity, affected-arm ground truth, hidden Cole parameters, diagnosis, or disease probability.

`EngineeringViewSnapshot` projects authoritative pipeline stages, acquisition quality, simulated BIS, processed features, baseline state, verified TinyML metadata/inference, temporal history, confounder evidence, decision configuration, subsystem health, and explicit simulated-versus-executable provenance.

`LabViewSnapshot` is an engineering projection permitted to contain scenario ID/type, configured side, and progression. It places this ground truth beside independently observed runtime evidence. Scenario fields remain forbidden from feature, ML, temporal, confounder, decision, patient, and clinician contracts.

`DigitalTwinInspectorSnapshot` is an additional engineering-only contract permitted to expose ground truth. It contains `DigitalTwinArmParameters`, additive `DigitalTwinParameterModifier` values, read-only `DigitalTwinEvolutionPoint` previews, ideal `DigitalTwinSpectrumPoint` series, an optional latest acquired noisy sweep, `DigitalTwinFitComparison` rows, and a compact `VirtualSensorInspectorSummary`. Its hidden values are presentation-only and are not inputs to processing or intelligence services.

`AequorTimelineEvent` stores a monotonic sequence index, authoritative simulated time, event/source provenance, and deep-copied nullable summaries for measurement, ML, temporal, confounder, and decision evidence. Scenario ground truth is nullable and engineering-only. `ReplaySession` describes the current reset boundary; `TimelineReplaySnapshot` contains ordered events, recorded trend series, and decision-derived state bands. With `include_ground_truth=false`, scenario events are omitted and every remaining ground-truth field is null. Replay projection never recomputes historical evidence.

`PrivacyInspectorSnapshot` contains classified data sources, local processing stages, exact application/data-flow topology, honest storage and reset lifetimes, network/external-service dependencies, live model metadata, audience boundaries, missing production controls, and separately labeled future hardware. It is an engineering transparency DTO, not evidence of compliance or a security certification.

`ChallengeDefinition` describes a test condition and expected engineering invariant. `ChallengeResult` records wall/simulated times, PASS/FAIL/INCONCLUSIVE, `ChallengeEvidence`, explanation, and runtime-cycle references. Status derives from nullable named invariant checks: all decisive checks true is PASS, any false is FAIL, and no decisive observation is INCONCLUSIVE. Challenge identity exists only in orchestration/result contracts and is excluded from intelligence and product-view contracts.

`VerificationCheck`, `VerificationSection`, and `VerificationReport` form the release-evidence contract. Each check carries a stable ID, category, PASS/FAIL/WARNING/SKIPPED status, critical flag, duration, evidence, details, and nullable failure reason. The report includes revision, timestamps, source revision, model hash, totals, overall gate status, scenario summary, and known warnings.

`CompetitionDemoSnapshot` is a presentation projection over existing authoritative state. Its trend points contain recorded simulated time, bilateral relative patterns, model novelty, temporal evidence, ADI, and surveillance state only when those values were emitted by a real integrated cycle. Ground truth is separately labeled and never copied into intelligence input contracts.

Contracts reject unknown fields, invalid enum members, impossible normalized-score ranges, non-positive frequencies and speed multipliers, invalid phase ranges, and inconsistent impedance magnitude. These checks enforce structural integrity only and are not medical validation.
