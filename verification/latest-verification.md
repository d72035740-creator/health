# Aequor Release Verification

**Status:** READY
**Revision:** aequor-release-verification-v1
**Checks:** 95 passed, 0 failed, 0 warnings, 0 skipped

## Environment and model artifact

- **PASS** `environment.python` — Supported Python runtime
- **PASS** `environment.file.package.json` — Required file: package.json
- **PASS** `environment.file.package-lock.json` — Required file: package-lock.json
- **PASS** `environment.file.aequor-ae-v1-int8.tflite` — Required file: aequor-ae-v1-int8.tflite
- **PASS** `environment.file.aequor-ae-v1.metadata.json` — Required file: aequor-ae-v1.metadata.json
- **PASS** `environment.model_hash` — Model SHA-256 matches metadata
- **PASS** `environment.model_load` — INT8 model loads
- **PASS** `environment.tensor_shape` — Model tensor shapes match 34-value adapter
- **PASS** `environment.quantization` — INT8 quantization metadata exists

## Core service readiness

- **PASS** `services.digital_patient` — Digital Patient ready
- **PASS** `services.bis_digital_twin` — Bis Digital Twin ready
- **PASS** `services.virtual_imu` — Virtual Imu ready
- **PASS** `services.virtual_temperature` — Virtual Temperature ready
- **PASS** `services.virtual_contact` — Virtual Contact ready
- **PASS** `services.quality` — Quality ready
- **PASS** `services.signal_processing` — Signal Processing ready
- **PASS** `services.baseline` — Baseline ready
- **PASS** `services.scenario` — Scenario ready
- **PASS** `services.ml` — Ml ready
- **PASS** `services.temporal` — Temporal ready
- **PASS** `services.confounder` — Confounder ready
- **PASS** `services.decision` — Decision ready
- **PASS** `services.runtime` — Integrated runtime ready

## Deterministic reset

- **PASS** `reset.baseline` — Baseline reset
- **PASS** `reset.scenario` — Scenario reset
- **PASS** `reset.temporal` — Temporal history empty
- **PASS** `reset.decision` — Decision history empty
- **PASS** `reset.runtime` — Runtime history empty
- **PASS** `reset.indices` — Acquisition indices reset
- **PASS** `reset.reproducible` — Startup sequence reproduces deterministically

## Baseline calibration

- **PASS** `baseline.ready` — Baseline reaches READY
- **PASS** `baseline.count` — Exactly 28 qualified observations enrolled
- **PASS** `baseline.span` — Minimum simulated span satisfied
- **PASS** `baseline.revisions` — Feature and baseline revisions match
- **PASS** `baseline.scenario` — Calibration remained baseline-stable

## Baseline-stable complete path

- **PASS** `stable.quality` — Stable path produces quality
- **PASS** `stable.bis` — Stable path produces bis
- **PASS** `stable.features` — Stable path produces features
- **PASS** `stable.baseline_comparison` — Stable path produces baseline_comparison
- **PASS** `stable.tflite` — Stable path produces tflite
- **PASS** `stable.temporal` — Stable path produces temporal
- **PASS** `stable.confounder` — Stable path produces confounder
- **PASS** `stable.decision` — Stable path produces decision
- **PASS** `stable.state` — Stable cycles remain within personal baseline

## Technical quality gating

- **PASS** `quality.active-motion` — ACTIVE MOTION blocks rejected downstream data
- **PASS** `quality.poor-contact` — POOR CONTACT blocks rejected downstream data
- **PASS** `quality.posture-transition` — POSTURE TRANSITION blocks rejected downstream data

## Longitudinal scenarios

- **PASS** `longitudinal.left` — Slow LEFT direction and persistence
- **PASS** `longitudinal.right` — Slow RIGHT reverses direction
- **PASS** `longitudinal.symmetry` — LEFT/RIGHT ADI within engineering tolerance
- **PASS** `longitudinal.systemic` — Systemic evidence rises and restrains unilateral escalation
- **PASS** `longitudinal.transient` — One transient does not create persistent state
- **PASS** `longitudinal.reset` — Scenario reset alone preserves decision
- **PASS** `longitudinal.recovery` — Future observations permit recovery

## Safe model failure behavior

- **PASS** `model_failure.unavailable` — Missing model produces no fake downstream output
- **PASS** `model_failure.restored` — Normal interpreter restored
- **PASS** `model_failure.hash` — Isolated hash mismatch rejected

## Anti-leakage and product boundaries

- **PASS** `boundaries.leakage` — Scenario/challenge fields absent from intelligence contracts
- **PASS** `boundaries.patient` — Patient projection is minimized
- **PASS** `boundaries.clinician` — Clinician projection remains scenario-blind
- **PASS** `boundaries.engineering` — Ground truth limited to designed engineering views

## Stale-cycle and replay integrity

- **PASS** `stale.cycle` — Rejected cycle does not inherit AI output
- **PASS** `replay.order` — Timeline events append in order
- **PASS** `replay.rejected` — Rejected replay event has no fake AI
- **PASS** `replay.observer` — Observer replay strips ground truth

## Privacy consistency and adversarial suite

- **PASS** `privacy.local` — Privacy DTO reports local INT8 inference
- **PASS** `privacy.cloud` — Privacy DTO reports no cloud/model API
- **PASS** `privacy.future` — Hardware deployment explicitly future
- **PASS** `privacy.copy` — No unsupported positive claims
- **PASS** `adversarial.critical` — Critical adversarial invariants pass
- **PASS** `adversarial.noncritical` — Noncritical adversarial outcomes recorded

## API, WebSocket, and frontend routes

- **PASS** `api.health` — API smoke /health
- **PASS** `api.api.v1.system.status` — API smoke /api/v1/system/status
- **PASS** `api.api.v1.runtime.status` — API smoke /api/v1/runtime/status
- **PASS** `api.api.v1.views.patient` — API smoke /api/v1/views/patient
- **PASS** `api.api.v1.views.clinician` — API smoke /api/v1/views/clinician
- **PASS** `api.api.v1.views.engineering` — API smoke /api/v1/views/engineering
- **PASS** `api.api.v1.views.lab` — API smoke /api/v1/views/lab
- **PASS** `api.api.v1.views.digital-twin` — API smoke /api/v1/views/digital-twin
- **PASS** `api.api.v1.views.timeline` — API smoke /api/v1/views/timeline
- **PASS** `api.api.v1.views.privacy` — API smoke /api/v1/views/privacy
- **PASS** `api.api.v1.challenges` — API smoke /api/v1/challenges
- **PASS** `api.api.v1.demo.status` — API smoke /api/v1/demo/status
- **PASS** `websocket.runtime` — Runtime WebSocket connects and publishes cycle update
- **PASS** `frontend.home` — Frontend route source /
- **PASS** `frontend.patient` — Frontend route source /patient
- **PASS** `frontend.clinician` — Frontend route source /clinician
- **PASS** `frontend.engineering` — Frontend route source /engineering
- **PASS** `frontend.lab` — Frontend route source /lab
- **PASS** `frontend.digital-twin` — Frontend route source /digital-twin
- **PASS** `frontend.timeline` — Frontend route source /timeline
- **PASS** `frontend.privacy` — Frontend route source /privacy
- **PASS** `frontend.challenge` — Frontend route source /challenge
- **PASS** `frontend.demo` — Frontend route source /demo
- **PASS** `frontend.build_config` — Frontend package scripts available

## Known limitations

- Synthetic sensing is not clinical or hardware validation.
- Security controls remain prototype-only.
