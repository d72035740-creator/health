# Architecture

## Phase 4 boundary

Phase 0 established infrastructure, Phase 1 added the Digital Patient and authoritative longitudinal clock, Phase 2 added bilateral raw BIS, and Phase 3 adds raw bilateral virtual wearable sensing. Phase 3 deliberately stops before measurement quality, signal processing, personalization, ML, temporal reasoning, confounder reasoning, decision logic, persistence, or patient/clinician analytics.

## Dependency direction

```text
Next.js presentation (never owns simulation time)
    │ REST controls/status + WebSocket clock events
    ▼
FastAPI transport adapters
    │
    ▼
Digital Patient Engine
    │ authoritative simulated time + seeded RNG
    ▼
Bioimpedance Digital Twin
    │ raw synchronized bilateral sweep
    ▼
Domain contracts and source protocols
    │
    ├── future sensor implementations
    └── future processing/intelligence stages
```

The backend is the sole future owner of measurement quality, filtering, feature extraction, baselines, inference, persistence, the Aequor Differential Index, and surveillance-state transitions. The frontend may format or label authoritative results, but must not recreate or infer them.

## Backend modules

| Module | Current responsibility | Explicit non-responsibility |
| --- | --- | --- |
| `api/routes` | Health, system status, and simulation lifecycle transport | No measurement endpoints |
| `api/websocket` | System heartbeat and authoritative simulation-clock events | No sensor frames or medical values |
| `core` | Environment settings and structured logging | No domain decisions |
| `domain` | Enums, Pydantic contracts, source protocols | No acquisition or algorithms |
| `simulation` | Synthetic identity, lifecycle, clock, RNG, bilateral Cole-model acquisition, reset hooks | No IMU/temperature/contact or disease simulation |
| `quality` | Reserved quality-engine boundary | No gating or quality scores |
| `signal_processing` | Reserved processing boundary | No filters or features |
| `baseline` | Reserved personalization boundary | No baselines |
| `ml` | Reserved model boundary | No TensorFlow/TFLite/inference |
| `temporal` | Reserved temporal boundary | No EWMA/CUSUM/persistence |
| `confounders` | Reserved reasoning boundary | No confounder classification |
| `decision` | Reserved decision boundary | No ADI or clinical state logic |
| `persistence` | Reserved storage boundary | No database or SQLite models |

The sensor `Protocol` interfaces separate acquisition from downstream consumers. A future `DigitalTwinBioimpedanceSource` and `AD5940BioimpedanceSource` can satisfy the same `BioimpedanceSource` boundary. The same applies to digital-twin and LSM6DSOX motion sources. No concrete sources are implemented yet.

## Authoritative simulation clock

`DigitalPatientEngine` is the sole owner of `simulation_id`, `patient_id`, seed, lifecycle, speed, and simulated time. `AuthoritativeSimulationClock` stores a simulated-time anchor and a monotonic-time anchor. While running, current simulated time is computed as:

```text
simulated anchor + (current monotonic time − monotonic anchor) × speed multiplier
```

This avoids accumulated tick drift. Pause captures the current value and freezes it. Resume installs a new monotonic anchor, so paused wall time cannot create a jump. A speed change first captures time under the old rate, then installs the new rate. Reset restores the configured starting instant exactly.

`SimulationRandom` owns a private seeded generator and stable namespaced seed derivation. It never mutates Python's global random state. Future simulation modules must receive randomness from this owner and use the engine's reset-hook boundary; they must not create independent clocks.

## Bioimpedance Digital Twin

The ideal `ColeImpedanceModel` is pure and independently testable. It produces one complex value per frequency using `Z(ω) = R∞ + (R0 − R∞) / (1 + (jωτ)^β)`. `DigitalTwinBioimpedanceSource` then applies bounded seed-derived noise to the complex R/X components and derives magnitude/phase from that same result.

`BilateralBioimpedanceService` owns a sweep index and captures one Digital Patient snapshot before producing both arm sweeps. The pair receives one deterministic `pair_id`, one index, one wall-clock timestamp, and one simulated timestamp. Reset hooks restore the index to zero, so the first post-reset acquisition produces the same deterministic noise sequence for the same seed. The source protocol preserves a later replacement path for an `AD5940BioimpedanceSource`.

Phase 2 output is raw/unqualified only. Future measurement-quality and signal-processing modules consume `BilateralBioimpedanceSweep`; they do not recreate clocks or reinterpret synthetic provenance as measured physiology.

## Virtual wearable sensor layer

`WearableSensorService` captures exactly one Digital Patient snapshot and never mutates the Phase 1 clock. `WearableSensorWindow` records that snapshot as `anchor_simulated_time` and `anchor_wall_clock_time`; individual samples use acquisition-local `relative_time_seconds`. The sources are independent of the BIS digital twin: Phase 4 may later connect raw windows to quality gating and then BIS acquisition.

The IMU convention is sensor x-forward, y-right, z-up. A 9.80665 m/s² gravity vector is projected using coherent roll/pitch. Posture derivatives drive gyro values and active motion uses smooth sinusoids, not independent random samples. Temperature is synthetic skin temperature, and contact is raw impedance rather than a quality score. Namespaced seed derivation by modality, arm, and window index preserves deterministic reset behavior.

## Measurement quality and gated acquisition

```text
Raw Sensor Window → Measurement Quality Engine → Qualified? ── No → BIS blocked
                                                        └──── Yes → BIS Digital Twin → Raw BIS Sweep
```

The engine extracts unit-explicit motion, posture, contact, temperature, and bilateral-integrity features, maps them monotonically to 0–100 engineering subscores, and applies centralized `quality-v1` prototype thresholds. A `MeasurementAttemptService` owns orchestration: rejected windows return no BIS and do not advance the BIS index; qualified windows trigger one synchronized bilateral sweep. This is technical acquisition suitability, not patient health or disease inference.

## BIS signal processing

```text
Qualified Measurement → Bilateral BIS → Complex Validation → Feature Processor → Processed Feature Snapshot → Phase 6 Baseline
```

`BISFeatureProcessor` consumes only the acquired qualified sweep. It reconstructs/checks complex R/X values, computes signed bilateral ratios/differences, fits spectral slopes against `log10(frequency_hz)`, and estimates Cole parameters with bounded deterministic optimization over observed R/X residuals. It never imports or receives the digital twin's hidden generating parameters. Processing failure is distinct from acquisition rejection; fitted fields remain explicitly unavailable when a fit fails.

## Personalized baseline and scenarios

```text
Processed Features → Baseline Calibration → Robust Personal Distribution → Signed Baseline Comparison
Authoritative Simulation Time → Scenario Engine → Effective Hidden Cole Parameters → BIS Twin → normal pipeline
```

The baseline engine accepts only qualified processed snapshots and enforces `bis-features-v1`. The scenario provider is an input-layer dependency of the BIS source; it alters effective Cole parameters by simulated time, but never imports signal-processing or baseline-comparison structures. Scenario truth is exposed only by its engineering control API.

## TinyML and TFLite inference

```text
Qualified processed features → Phase 6 robust normalization → fixed 34-value ML vector
Baseline-stable corpus → deterministic autoencoder training → Keras/float32 TFLite/INT8 TFLite
Qualified attempt + READY baseline → verified INT8 LiteRT interpreter → reconstruction MSE → model novelty
```

The ML adapter is versioned `aequor-ml-input-v1` and clips normalized values to the configured bounded range. Training uses baseline-stable observations only and never receives scenario type or severity. Runtime loads the INT8 artifact once, verifies its SHA-256 metadata, reads tensor quantization parameters, quantizes input, invokes the TFLite interpreter, dequantizes output, and computes reconstruction error. There is no Keras fallback or synthetic score: missing, corrupt, or incompatible artifacts yield `ML INFERENCE UNAVAILABLE` and subsystem `ERROR`.

## Frontend modules

- `app` owns App Router entry points and global presentation tokens.
- `components/layout` owns the persistent product frame.
- `components/system` renders authoritative service and subsystem states.
- `components/ui` contains small presentation primitives.
- `lib/api` and `lib/websocket` isolate transport behavior.
- `lib/types` mirrors the transport schema for compile-time use; backend Pydantic models remain authoritative.

REST status is polled so recovery from a backend outage updates the shell. Both WebSocket clients reconnect with bounded exponential backoff. A failed REST request results in `DISCONNECTED`; cached values are not shown as live readiness. When the simulation stream is disconnected, the UI freezes/hides authoritative time and does not substitute a browser clock. Both streams contain infrastructure state only.

## Failure and language policy

Unavailable components report `DISCONNECTED` or `ERROR`. Capabilities not yet built report `NOT_IMPLEMENTED`. No layer substitutes random values. Future surveillance language is limited to conservative states such as `OBSERVING_CHANGE` and `CLINICAL_REVIEW_RECOMMENDED`; contracts intentionally contain no positive diagnosis state.
