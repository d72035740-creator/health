# Aequor Health

Aequor Health is a proposed bilateral wearable surveillance platform for detecting persistent physiological changes associated with possible early lymphedema. The eventual system is intended to combine multi-frequency bioimpedance, motion, skin-temperature, and electrode-contact sensing with local Edge-AI processing.

> **Phase 12 + 13 prototype disclaimer:** This repository is not a clinically validated diagnostic system. ADI and surveillance states are prototype research/workflow outputs only; they are not diagnosis, disease risk, or clinical probability.

## Current scope

This repository implements **Phase 12 + 13 — Aequor Decision Engine & Integrated Runtime**, while preserving the earlier foundation:

- a Next.js/TypeScript/Tailwind product shell;
- a FastAPI/Pydantic backend shell;
- explicit domain and unit contracts;
- replaceable sensor-source protocols;
- authoritative REST system and simulation lifecycle APIs;
- non-medical system-heartbeat and simulation-clock WebSockets;
- one clearly synthetic local demo patient;
- deterministic seed ownership, time acceleration, pause/resume/reset, and manual stepping;
- a synchronized bilateral multi-frequency Cole-model digital twin;
- bounded deterministic synthetic instrumentation noise;
- raw/unqualified bilateral acquisition REST API and engineering visualizations;
- synchronized 3-second bilateral virtual wearable windows (50 Hz IMU, 4 Hz skin temperature, 12 Hz contact impedance);
- centralized prototype technical-quality scoring and conditional BIS acquisition;
- deterministic named bilateral BIS feature extraction after qualified acquisition;
- robust personalized baseline statistics and signed baseline-relative comparisons;
- hidden-physiology longitudinal scenarios that perturb only the digital-twin input layer;
- a deterministic baseline-only autoencoder corpus and versioned `aequor-ml-input-v1` vector adapter;
- exported Keras, float32 TFLite, and fully quantized INT8 TFLite model artifacts with hash metadata;
- strict local INT8 TFLite inference with runtime quantization/dequantization and no Keras/fallback scoring;
- explicit ML status/model APIs and artifact-removal failure behavior (`ML INFERENCE UNAVAILABLE`);
- time-aware EWMA, one-sided CUSUM, persistence, trend, recovery, and temporal engineering states;
- scenario-blind bilateral/unilateral, temperature, contact, motion, and transient evidence reasoning;
- explicit ADI components/modifiers, hysteretic surveillance state machine, and deterministic explanations;
- one authoritative integrated runtime measurement-cycle endpoint;
- structured backend logging and focused tests; and
- documented boundaries for later phases.

The backend owns the one authoritative simulation clock and all future domain intelligence. The frontend presents backend snapshots/events and never advances an independent simulation clock. See [Architecture](docs/ARCHITECTURE.md), [Data contracts](docs/DATA_CONTRACTS.md), and [Phases](docs/PHASES.md).

## Simulation controls

The local demo session starts in `READY`. Valid lifecycle transitions are `READY → RUNNING → PAUSED → RUNNING`; reset returns `READY` from an initialized state. Invalid transitions return HTTP 409 and are never silently accepted.

- **Start / Pause / Resume / Reset** operate on the backend lifecycle.
- **Speed** accepts 0.1× through 86,400×. At 21,600×, one real second represents six simulated hours. A running speed change preserves the exact current simulated time and applies the new rate forward.
- **Manual step** accepts an explicit number of simulated seconds while `READY` or `PAUSED`; it is rejected while `RUNNING`.
- **Seed `42017`** belongs to the simulation session. Future stochastic modules must derive randomness from the engine-owned deterministic source rather than Python global randomness.
- **Reset** restores the exact configured simulated start time, preserves the configured seed, resets deterministic RNG state, runs registered future-module reset hooks, and returns the lifecycle to `READY`.

## Bilateral bioimpedance digital twin

Phase 2 adds manually triggered, synchronized left/right raw sweeps at 5, 10, 20, 50, 100, and 200 kHz. Every sweep is explicitly `SIMULATED` and `RAW_UNQUALIFIED`; Phase 4 will decide measurement quality. The backend alone generates sweeps—no biomedical data is generated in the browser.

The ideal complex impedance equation is:

```text
Z(ω) = R∞ + (R0 − R∞) / (1 + (jωτ)^β),  where ω = 2πf
```

`beta` is the dimensionless dispersion exponent (`0 < beta ≤ 1`), avoiding ambiguity with other alpha conventions. Resistance, reactance, magnitude, and phase are all derived from the same complex `Z`; magnitude and phase are never independently randomized.

Synthetic arm parameters are prototype demonstration settings, not clinical reference ranges. A bounded, zero-mean-in-expectation instrumentation-noise layer applies deterministic seed-derived perturbations to R/X only. It is not derived from characterization of the final AD5940 wearable. Reset returns the sweep index and deterministic noise sequence to the initial state.

The Phase 2 acquisition API is:

```text
GET  /api/v1/bioimpedance/config
POST /api/v1/bioimpedance/sweep
```

## Virtual wearable sensor layer

Phase 3 adds manually requested bilateral raw sensor windows. Each captures one **anchor simulated time** and one wall-clock anchor, then uses `relative_time_seconds` from 0.0 to 3.0 seconds for local physical acquisition. Generating a window never advances or stretches the Phase 1 longitudinal simulation clock.

Each band has a synthetic 6-axis IMU, synthetic skin temperature, and raw electrode `contact_impedance_ohm`. IMU gravity uses 9.80665 m/s² and coherent orientation/motion presets; temperature and contact signals vary slowly or smoothly with bounded deterministic prototype instrumentation noise. These are engineering behaviors, not characterized device performance or clinical reference values.

```text
GET  /api/v1/virtual-sensors/config
POST /api/v1/virtual-sensors/window
```

Windows are `SIMULATED` and `RAW_UNQUALIFIED` at the Phase 3 source boundary. Namespaced seeds by modality, arm, and window index make reset reproducible and keep sensor streams independent from BIS calls.

Phase 4 adds `POST /api/v1/measurement/attempt`: a raw window is evaluated by the Measurement Quality Engine and a bilateral BIS sweep is acquired only when the technical window is `QUALIFIED`. Thresholds are centralized, versioned as `quality-v1`, explicitly labeled prototype engineering thresholds, and are not clinically validated. Rejected attempts never consume a BIS sweep index.

Phase 5 extends qualified attempts with `processed_features`. The processor validates complex R/X/magnitude/phase consistency, computes signed bilateral frequency features and log-frequency spectral slopes, and performs a bounded deterministic complex Cole fit from observed sweep values only. Features are versioned `bis-features-v1`; they are processed mathematical transformations, not biomarkers, risk, or diagnosis. Cole-fit parameters remain nullable on failure and are excluded from the fixed ML-vector adapter when unavailable.

Phase 6 baseline calibration consumes only qualified processed features, requires 28 observations spanning at least seven simulated days, and stores median/MAD/IQR robust statistics under `baseline-v1`. Phase 7 scenarios change hidden Cole parameters before acquisition; they never directly modify features or baseline comparisons. Scenario progression follows authoritative simulated time, and scenario reset preserves a completed baseline while full simulation reset clears it. Phase 8 trains only on baseline-stable vectors normalized by the exact Phase 6 robust statistics. Phase 9 invokes only the verified INT8 artifact after a qualified attempt with a READY baseline; missing, corrupt, or incompatible artifacts produce an explicit unavailable state.

## Prerequisites

- Python 3.11 or newer
- Node.js 20.9 or newer (Node 24 was used for verification)
- npm 10 or newer

## Installation

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
npm --prefix frontend install
Copy-Item .env.example .env
Copy-Item .env.example frontend\.env.local
```

The backend reads the root process environment. PowerShell users may set values for a session with `$env:AEQUOR_LOG_LEVEL = "DEBUG"`. Next.js reads the `NEXT_PUBLIC_*` values from `frontend/.env.local`.

## Run locally

Open two terminals from the repository root.

Backend:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --app-dir backend --env-file .env --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm --prefix frontend run dev
```

Open `http://localhost:3000`. API documentation is available locally at `http://localhost:8000/docs`.

## Test and build

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest backend\tests
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `AEQUOR_ENV` | `development` | Backend runtime environment label |
| `AEQUOR_LOG_LEVEL` | `INFO` | Python logging threshold |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Browser REST base URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/ws/system` | Browser system-heartbeat endpoint |
| `NEXT_PUBLIC_SIMULATION_WS_URL` | `ws://localhost:8000/ws/simulation` | Browser authoritative simulation-clock endpoint |

The defaults are local-development values, not production addresses. This project has no cloud dependency and no persistence layer in Phase 2.

## Repository layout

```text
aequor-health/
├── backend/          FastAPI service, domain contracts, boundaries, and tests
├── frontend/         Next.js product shell and REST/WebSocket clients
├── docs/             Architecture, data-contract, and roadmap documentation
├── scripts/          Reserved for repeatable developer tooling
├── .env.example      Documented local configuration
└── README.md
```

TinyML artifacts are stored in `models/`. TensorFlow training is supported in the Python 3.12 `.venv-ml` environment; the backend can run the exported INT8 model with LiteRT in the regular environment. Phase 10 uses simulated timestamps (not measurement counts) for temporal evidence, and Phase 11 consumes observed outputs only.

# health
