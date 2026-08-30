# Aequor Health

Aequor Health is a proposed bilateral wearable surveillance platform for detecting persistent physiological changes associated with possible early lymphedema. The eventual system is intended to combine multi-frequency bioimpedance, motion, skin-temperature, and electrode-contact sensing with local Edge-AI processing.

> **Phase 2 prototype disclaimer:** This repository is not a clinically validated diagnostic system. The Digital Patient and bilateral bioimpedance data are synthetic digital-twin outputs, not real patient data or validated physiological measurements. It contains no quality engine, signal processing, trained model, anomaly score, risk value, or medical decision logic.

## Current scope

This repository implements **Phase 2 — Bilateral Bioimpedance Digital Twin**, while preserving the Phase 0–1 foundation:

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

# health
