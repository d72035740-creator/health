# Architecture

## Phase 2 boundary

Phase 0 established executable infrastructure and contracts. Phase 1 added the synthetic Digital Patient identity and deterministic simulation-session lifecycle. Phase 2 adds only synthetic bilateral multi-frequency bioimpedance acquisition. It deliberately stops before IMU, temperature, contact, measurement quality, signal processing, personalization, ML, temporal reasoning, confounder reasoning, decision logic, persistence, or patient/clinician analytics.

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
