# Aequor competition demo script

## Before presenting

Start the backend and frontend using the README commands, open `/demo`, and select **Reset Demo**. Keep the persistent disclosure visible: sensing is simulated; the processing stack is executable software. Never describe a surveillance state as a diagnosis or quote the ADI as clinical risk.

## 90-second demo

**0–10 seconds — concept.** “Aequor explores personalized, bilateral physiological surveillance. It learns an individual reference instead of applying a universal threshold.” Point to the simulated-versus-real badge.

**10–25 seconds — personal baseline.** Select **Establish Personalized Baseline**. Explain that the button runs 28 qualified observations over the required simulated span through the real signal-processing and baseline services.

**25–45 seconds — slow unilateral experiment.** Verify one stable pattern, then select **Start Slow LEFT Demo**. The orchestrator selects the scenario, advances authoritative time, and requests measurements; it does not set any result.

**45–60 seconds — local intelligence.** Use the synchronized chart and Ground Truth versus Aequor Observed cards. Call out the real local INT8 model, temporal persistence, observed side, ADI, and state. Say: “Scenario identity is not provided to the intelligence pipeline.”

**60–70 seconds — patient view.** Open Patient. Show calm state language, measurement eligibility, and the personal trend without raw engineering internals.

**70–80 seconds — clinician view.** Open Clinician. Show richer bilateral, persistence, quality, and explanation evidence. State that ADI is an engineering index, not probability or diagnosis.

**80–90 seconds — robustness.** Open Challenge. Mention motion rejection, systemic-vs-unilateral reasoning, stale-cycle protection, model-unavailable behavior, and anti-leakage checks. Close: “Personalized, quality-aware, local, longitudinal, explainable—and explicit about what is simulated.”

## 3–5 minute technical demo

1. **Boundary (20 seconds).** On the landing page, separate simulated physiology/acquisition from executable quality, BIS processing, baseline, TFLite, temporal, confounder, and decision software.
2. **Baseline (30 seconds).** In `/demo`, reset and establish the baseline. Explain 28 qualified observations and that rejected measurements cannot enroll.
3. **Stable cycle (20 seconds).** Run the stable verification. Show that a qualified cycle reaches every downstream stage and generally remains within the personal reference.
4. **Slow unilateral progression (45 seconds).** Start slow LEFT. Explain the three two-day checkpoints. Read actual LEFT/RIGHT pattern, novelty/temporal evidence, ADI, and state from the synchronized visualization.
5. **Patient dashboard (20 seconds).** Show the concise state, personal trend, skipped-attempt language, and unobtrusive prototype disclosure.
6. **Clinician dashboard (30 seconds).** Show the current state, observed direction, persistence, bilateral evidence, quality context, and explanations. Keep the ADI limitation adjacent.
7. **Active-motion rejection (20 seconds).** In Challenge or Lab, run active motion. Confirm rejection and the absence of BIS, ML, temporal, confounder, and decision updates for that attempt.
8. **Systemic bilateral challenge (25 seconds).** Run the systemic challenge. Compare bilateral evidence with restrained unilateral interpretation; do not claim a clinical classification.
9. **Local-model proof (25 seconds).** Show model-unavailable challenge evidence or the release report. Explain that an absent/hash-invalid artifact produces `ML_UNAVAILABLE`, no novelty, and no downstream update; restoring it restores actual inference.
10. **Conclusion (15 seconds).** Show Timeline and Privacy briefly: evidence is recorded in order, observer mode strips ground truth, core inference uses no cloud model API, and current storage is local/in-memory. End with the seven-part story: personalized, quality-aware, edge AI, longitudinal, explainable, privacy-oriented, honest.

## Recovery if a demo action fails

Use **Reset Demo**, wait for the status to reload, and repeat the guided sequence once. If the backend is unavailable, stop and show the explicit error rather than describing cached values. If ML is unavailable, show that state as the intended fail-closed behavior and restore the committed artifact before continuing.
