"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { connectRuntimeSocket, type RuntimeConnectionState } from "@/lib/websocket/runtime-socket";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type DemoTrendPoint = {
  simulated_time: string;
  left_relative_pattern: number | null;
  right_relative_pattern: number | null;
  novelty_z: number | null;
  ewma: number | null;
  adi: number | null;
  surveillance_state: string;
};

type PipelineStep = {
  id: string;
  label: string;
  sublabel: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "BLOCKED" | "NOT_RUN" | "REJECTED";
};

type ChallengeResult = {
  challenge_id: string;
  title: string;
  status: "PASS" | "FAIL" | "INCONCLUSIVE";
  explanation: string;
  expected_invariant: string;
  observed_evidence: {
    observations: Record<string, unknown>;
    invariant_checks: Record<string, boolean | null>;
  };
};

type PatientPreview = {
  synthetic_patient?: { display_name?: string };
  surveillance_state?: string;
  state_title?: string;
  state_message?: string;
  recommended_message?: string;
  fluid_balance_summary?: {
    left_relative_index?: number;
    right_relative_index?: number;
    bilateral_pattern_difference?: number;
  };
};

type ClinicianPreview = {
  surveillance_state?: string;
  dominant_observed_side?: string;
  adi?: number | null;
  quality_summary?: { latest_score?: number | null };
  temporal_summary?: { persistence_duration_days?: number };
};

type DemoSnapshot = {
  title: string;
  step_index: number;
  total_steps: number;
  step_title: string;
  busy: boolean;
  baseline: {
    state: string;
    observations: number;
    span_days: number;
  };
  scenario_ground_truth: {
    scenario_type?: string;
    affected_arm?: string;
    severity?: number;
    active?: boolean;
    simulated_time?: string;
  };
  observed: {
    quality?: string;
    quality_score?: number;
    rejection_reasons?: string[];
    pipeline_status?: string;
    dominant_observed_side?: string | null;
    novelty_z?: number | null;
    reconstruction_error?: number | null;
    personal_deviation_summary?: string;
    ewma?: number | null;
    cusum?: number | null;
    persistence_days?: number | null;
    systemic_evidence?: number;
    systemic_label?: string;
    unilateral_evidence?: number | null;
    adi?: number | null;
    surveillance_state?: string;
    decision_updated?: boolean;
    cycle_index?: number;
    simulated_time?: string;
  } | null;
  trend: DemoTrendPoint[];
  runtime_cycle_ids: string[];
  disclosure: string;
  automation_boundary: string;
  checkpoint_index?: number;
  total_checkpoints?: number;
  active_experiment?: string | null;
  patient_preview?: PatientPreview | null;
  clinician_preview?: ClinicianPreview | null;
};

const PIPELINE_FLOW_STEPS = [
  { id: "SENSORS", label: "Sensors", sublabel: "Virtual acquisition window" },
  { id: "QUALITY", label: "Quality", sublabel: "Technical artifact gating" },
  { id: "BIS", label: "BIS", sublabel: "Multi-frequency bilateral" },
  { id: "FEATURES", label: "Features", sublabel: "Signal processing" },
  { id: "BASELINE", label: "Baseline", sublabel: "Personalized reference" },
  { id: "TINYML", label: "Edge AI", sublabel: "Local INT8 autoencoder" },
  { id: "TEMPORAL", label: "Temporal", sublabel: "EWMA & persistence" },
  { id: "CONFOUNDERS", label: "Context", sublabel: "Confounder reasoning" },
  { id: "DECISION", label: "Decision", sublabel: "ADI & state machine" },
];

export function CompetitionDemo() {
  const [demo, setDemo] = useState<DemoSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [connection, setConnection] = useState<RuntimeConnectionState>("CONNECTING");
  const [activeAct, setActiveAct] = useState<1 | 2 | 3>(1);

  // Staged pipeline execution state for presentation replay
  const [pipelineState, setPipelineState] = useState<PipelineStep[]>(() =>
    PIPELINE_FLOW_STEPS.map((s) => ({ ...s, status: "PENDING" }))
  );
  const [pipelineMessage, setPipelineMessage] = useState<string | null>(null);
  const [pipelineRejected, setPipelineRejected] = useState(false);
  const [pipelineActive, setPipelineActive] = useState(false);

  // Challenge test tracking
  const [challengeResults, setChallengeResults] = useState<Record<string, ChallengeResult>>({});
  const [suiteSummary, setSuiteSummary] = useState<{ total: number; passed: number } | null>(null);

  // Smooth number interpolation state
  const [displayAdi, setDisplayAdi] = useState<number | null>(null);
  const [displayNovelty, setDisplayNovelty] = useState<number | null>(null);
  const [displayPersistence, setDisplayPersistence] = useState<number | null>(null);

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Load latest demo status
  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/demo/status`);
      if (!res.ok) throw new Error("Backend unavailable");
      const data: DemoSnapshot = await res.json();
      setDemo(data);
      setError(null);

      // Auto-advance act based on baseline
      if (data.baseline.state === "READY") {
        if (data.step_index >= 3) {
          // If slow left has finished or is in progress
          setActiveAct((prev) => (prev === 1 ? 2 : prev));
        }
      } else {
        setActiveAct(1);
      }

      // Smooth numbers update
      if (data.observed?.adi != null) {
        setDisplayAdi(Number(data.observed.adi));
      }
      if (data.observed?.novelty_z != null) {
        setDisplayNovelty(Number(data.observed.novelty_z));
      }
      if (data.observed?.persistence_days != null) {
        setDisplayPersistence(Number(data.observed.persistence_days));
      }
    } catch {
      setError("BACKEND UNAVAILABLE — Live evidence hidden to prevent stale display. Reconnecting...");
    }
  }, []);

  // WebSocket runtime connection & polling fallback
  useEffect(() => {
    const initialTimer = setTimeout(() => void loadStatus(), 0);
    const stopWs = connectRuntimeSocket(() => void loadStatus(), setConnection);
    const fallbackPoll = setInterval(() => void loadStatus(), 12000);
    return () => {
      clearTimeout(initialTimer);
      clearInterval(fallbackPoll);
      stopWs();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [loadStatus]);

  // Clean presentation replay sequence for normal checkpoint or measurement
  const replayPipeline = useCallback(
    (isRejected = false, rejectionReason?: string, onFinish?: () => void) => {
      setPipelineActive(true);
      setPipelineRejected(isRejected);
      const steps = [...PIPELINE_FLOW_STEPS];

      // Reset to pending
      setPipelineState(steps.map((s) => ({ ...s, status: "PENDING" })));
      setPipelineMessage("Acquiring sensor window and executing Aequor pipeline...");

      const stepDelay = isRejected ? 350 : 260;
      let current = 0;

      const runNextStep = () => {
        if (current >= steps.length) {
          setPipelineActive(false);
          setPipelineMessage("Authoritative runtime result committed.");
          if (onFinish) onFinish();
          return;
        }

        const step = steps[current];

        // Handle quality rejection condition (e.g. Active Motion)
        if (isRejected && step.id === "QUALITY") {
          setPipelineState((prev) =>
            prev.map((s, idx) => {
              if (idx < current) return { ...s, status: "COMPLETED" };
              if (idx === current) return { ...s, status: "REJECTED" };
              if (idx === current + 1) return { ...s, status: "BLOCKED" };
              return { ...s, status: "NOT_RUN" };
            })
          );
          setPipelineMessage(`MEASUREMENT STOPPED BEFORE AI — ${rejectionReason ?? "High Motion Artifact"}`);
          setPipelineActive(false);
          if (onFinish) onFinish();
          return;
        }

        setPipelineState((prev) =>
          prev.map((s, idx) => {
            if (idx < current) return { ...s, status: "COMPLETED" };
            if (idx === current) return { ...s, status: "RUNNING" };
            return { ...s, status: "PENDING" };
          })
        );

        current++;
        timerRef.current = setTimeout(runNextStep, stepDelay);
      };

      runNextStep();
    },
    []
  );

  // Execute demo actions with safety & staged visual animation
  const executeDemoAction = async (action: string) => {
    if (runningAction) return;
    setRunningAction(action);

    try {
      let endpoint = `${API}/api/v1/demo/${action}`;
      if (action === "start-slow-left") endpoint = `${API}/api/v1/demo/start-slow-left`;
      if (action === "checkpoint") endpoint = `${API}/api/v1/demo/checkpoint`;

      const response = await fetch(endpoint, { method: "POST" });
      if (!response.ok) throw new Error(String(response.status));

      const updated: DemoSnapshot = await response.json();
      setDemo(updated);
      setError(null);

      // Replay pipeline execution for checkpoints and stable measurement
      if (action === "checkpoint" || action === "stable" || action === "slow-left") {
        replayPipeline(false);
      } else if (action === "baseline") {
        setActiveAct(1);
      } else if (action === "reset") {
        setChallengeResults({});
        setSuiteSummary(null);
        setActiveAct(1);
        setPipelineState(PIPELINE_FLOW_STEPS.map((s) => ({ ...s, status: "PENDING" })));
        setPipelineMessage(null);
        setPipelineRejected(false);
      }
    } catch {
      setError("DEMO ACTION FAILED — Backend request was not committed. Try again.");
    } finally {
      setRunningAction(null);
    }
  };

  // Run isolated adversarial challenge (Act 3)
  const runChallenge = async (challengeId: string) => {
    if (runningAction) return;
    setRunningAction(challengeId);

    try {
      const response = await fetch(`${API}/api/v1/challenges/${challengeId}/run`, { method: "POST" });
      if (!response.ok) throw new Error(String(response.status));
      const res: ChallengeResult = await response.json();
      setChallengeResults((prev) => ({ ...prev, [challengeId]: res }));

      if (challengeId === "active-motion") {
        // Visual replay stops at Quality
        replayPipeline(true, "High Motion Artifact");
      }
    } catch {
      setError(`CHALLENGE ${challengeId} FAILED TO EXECUTE`);
    } finally {
      setRunningAction(null);
    }
  };

  // Run all 10 adversarial challenges
  const runAllChallenges = async () => {
    if (runningAction) return;
    setRunningAction("all-challenges");

    try {
      const response = await fetch(`${API}/api/v1/challenges/run-all`, { method: "POST" });
      if (!response.ok) throw new Error(String(response.status));
      const results: ChallengeResult[] = await response.json();
      const mapped: Record<string, ChallengeResult> = {};
      let passCount = 0;
      for (const r of results) {
        mapped[r.challenge_id] = r;
        if (r.status === "PASS") passCount++;
      }
      setChallengeResults(mapped);
      setSuiteSummary({ total: results.length, passed: passCount });
    } catch {
      setError("ROBUSTNESS SUITE EXECUTION FAILED");
    } finally {
      setRunningAction(null);
    }
  };

  if (error && !demo) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#050e0c] p-6 text-[#e8f1ee]">
        <div role="alert" className="max-w-md rounded-2xl border border-[#d6b570]/30 bg-[#161f1c] p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#d6b570]/10 text-[#d6b570]">
            ✕
          </div>
          <h2 className="mt-4 text-lg font-semibold tracking-wide text-[#e8f1ee]">BACKEND UNAVAILABLE</h2>
          <p className="mt-2 text-xs leading-5 text-[#8ca39c]">{error}</p>
          <button
            onClick={() => void loadStatus()}
            className="mt-6 rounded-full bg-[#62c9b4] px-6 py-2.5 text-xs font-semibold tracking-wider text-[#061210] hover:bg-[#7fe0cc]"
          >
            RETRY CONNECTION
          </button>
        </div>
      </main>
    );
  }

  const baselineReady = demo?.baseline.state === "READY";
  const groundTruth = demo?.scenario_ground_truth ?? {};
  const observed = demo?.observed;
  const currentCheckpoint = demo?.checkpoint_index ?? 0;
  const totalCheckpoints = demo?.total_checkpoints ?? 3;
  const progressionPct = Number(groundTruth.severity ?? 0) * 100;

  return (
    <main className="min-h-screen bg-[#050e0c] text-[#e8f1ee] antialiased selection:bg-[#62c9b4] selection:text-[#050e0c]">
      {/* Top Banner Alert if any transient error */}
      {error && (
        <div role="alert" className="border-b border-[#d6b570]/30 bg-[#251e12] px-5 py-2.5 text-center text-xs text-[#e8cb90]">
          {error}
        </div>
      )}

      {/* COMPACT PREMIUM HEADER */}
      <header className="sticky top-0 z-30 border-b border-white/[0.08] bg-[#050e0c]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1520px] flex-wrap items-center justify-between gap-4 px-6 py-3.5 sm:px-8">
          <div className="flex items-center gap-4">
            <a href="/" className="text-sm font-black tracking-[0.3em] text-[#62c9b4] hover:opacity-85">
              AEQUOR
            </a>
            <span className="hidden h-4 w-[1px] bg-white/15 sm:inline-block" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold tracking-wider text-white">LIVE EDGE-AI EXPERIMENT</span>
                <span className="rounded-full border border-[#62c9b4]/25 bg-[#62c9b4]/10 px-2.5 py-0.5 text-[9px] font-bold tracking-widest text-[#7fe0cc]">
                  SIMULATED SENSING · REAL EXECUTABLE AI
                </span>
              </div>
              <p className="hidden text-[11px] text-[#7d968f] md:block">
                Personalized bilateral surveillance using local TinyML and longitudinal reasoning.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[10px] text-[#8ea39c]">
              <span
                className={`h-2 w-2 rounded-full ${
                  connection === "CONNECTED" ? "bg-[#62c9b4] shadow-[0_0_8px_#62c9b4]" : "bg-[#d6b570]"
                }`}
              />
              <span>Runtime: {connection}</span>
            </div>

            <button
              onClick={() => void executeDemoAction("reset")}
              disabled={!!runningAction}
              className="rounded-full border border-white/15 bg-white/[0.04] px-4 py-1.5 text-[10px] font-bold tracking-wider text-[#98b0a9] transition hover:bg-white/[0.08] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              RESET DEMO
            </button>
          </div>
        </div>

        {/* 3-ACT NAVIGATION BAR */}
        <div className="border-t border-white/[0.05] bg-[#071311]">
          <div className="mx-auto flex max-w-[1520px] items-center justify-between px-6 sm:px-8">
            <div className="flex gap-1 overflow-x-auto py-2">
              <ActTab
                actNumber={1}
                title="LEARN MY BASELINE"
                active={activeAct === 1}
                completed={baselineReady}
                onClick={() => setActiveAct(1)}
              />
              <ActTab
                actNumber={2}
                title="WATCH AEQUOR REASON"
                active={activeAct === 2}
                completed={currentCheckpoint >= totalCheckpoints}
                onClick={() => setActiveAct(2)}
              />
              <ActTab
                actNumber={3}
                title="TRY TO FOOL AEQUOR"
                active={activeAct === 3}
                completed={Object.keys(challengeResults).length > 0}
                onClick={() => setActiveAct(3)}
              />
            </div>

            <span className="text-[10px] font-semibold tracking-wider text-[#637d75]">
              ACT {activeAct} OF 3
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1520px] px-5 py-6 sm:px-8">
        {/* ========================================================================= */}
        {/* ACT 1 — LEARN MY BASELINE */}
        {/* ========================================================================= */}
        {activeAct === 1 && (
          <section className="animate-fadeIn space-y-6">
            <div className="rounded-[2rem] border border-[#62c9b4]/20 bg-gradient-to-br from-[#0a1f1b] via-[#091a17] to-[#061412] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.4)] sm:p-12">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-[#62c9b4]/30 bg-[#62c9b4]/10 px-3 py-1 text-[10px] font-bold tracking-widest text-[#7fe0cc]">
                    <span>ACT 1 / 3</span> · <span>PERSONALIZED ENROLLMENT</span>
                  </div>
                  <h1 className="mt-4 text-3xl font-light tracking-tight text-white sm:text-5xl">
                    FIRST, AEQUOR LEARNS YOU.
                  </h1>
                  <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#9eb6ae] sm:text-base">
                    Aequor does not begin with a universal population threshold. It builds Maya&apos;s own bilateral
                    reference from qualified measurements over simulated time.
                  </p>
                  <div className="mt-4 flex items-center gap-2 text-xs text-[#718c84]">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#62c9b4]" />
                    <strong className="text-[#a4c2ba]">MAYA SEN</strong> · Synthetic demo patient
                  </div>
                </div>

                <div className="flex flex-col items-start gap-3 sm:items-end">
                  {!baselineReady ? (
                    <button
                      onClick={() => void executeDemoAction("baseline")}
                      disabled={!!runningAction}
                      className="group flex items-center gap-3 rounded-full bg-[#62c9b4] px-8 py-4 text-xs font-bold tracking-widest text-[#051310] shadow-[0_10px_30px_rgba(98,201,180,0.3)] transition hover:bg-[#7fe0cc] disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <span>{runningAction === "baseline" ? "LEARNING BASELINE…" : "ESTABLISH PERSONAL BASELINE"}</span>
                      <span className="transition-transform group-hover:translate-x-1">→</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => setActiveAct(2)}
                      className="group flex items-center gap-3 rounded-full bg-[#62c9b4] px-8 py-4 text-xs font-bold tracking-widest text-[#051310] shadow-[0_10px_30px_rgba(98,201,180,0.3)] transition hover:bg-[#7fe0cc]"
                    >
                      <span>START LIVE EXPERIMENT</span>
                      <span className="transition-transform group-hover:translate-x-1">→</span>
                    </button>
                  )}
                  <p className="text-[11px] text-[#69857d]">
                    Executes 28 real qualified acquisitions across 7.5 simulated days
                  </p>
                </div>
              </div>

              {/* Truthful Baseline Animated Sequence */}
              {runningAction === "baseline" && (
                <div className="mt-8 rounded-2xl border border-[#62c9b4]/30 bg-[#071714] p-6">
                  <div className="flex items-center gap-3">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#62c9b4] border-t-transparent" />
                    <span className="text-sm font-semibold tracking-wide text-[#7fe0cc]">
                      BUILDING PERSONAL REFERENCE
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-[#8da59e]">
                    Running 28 qualified pipeline measurements across seven simulated days...
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <ProgressPill step="1" label="Technical quality gating" active />
                    <ProgressPill step="2" label="Multi-frequency BIS" active />
                    <ProgressPill step="3" label="Signal processing" active />
                    <ProgressPill step="4" label="Personal baseline learning" active />
                  </div>
                </div>
              )}

              {/* Bilateral Arms Visual Representation */}
              <div className="mt-10 grid gap-6 md:grid-cols-2">
                <BilateralArmCard
                  side="LEFT ARM"
                  status={baselineReady ? "REFERENCE ESTABLISHED" : "UNINITIALIZED"}
                  value={baselineReady ? "100" : "LEARNING…"}
                  subtext="Personal reference point"
                  calibrated={baselineReady}
                />
                <BilateralArmCard
                  side="RIGHT ARM"
                  status={baselineReady ? "REFERENCE ESTABLISHED" : "UNINITIALIZED"}
                  value={baselineReady ? "100" : "LEARNING…"}
                  subtext="Personal reference point"
                  calibrated={baselineReady}
                />
              </div>

              <p className="mt-4 text-center text-[10px] uppercase tracking-widest text-[#5e7870]">
                Presentation and reference values only · Does not imply physical fluid volume
              </p>

              {/* Authoritative Confirmation after calibration */}
              {baselineReady && (
                <div className="mt-8 rounded-2xl border border-[#62c9b4]/30 bg-[#071a17]/90 p-6 backdrop-blur">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#62c9b4]/20 text-[#62c9b4]">
                        ✓
                      </div>
                      <div>
                        <h2 className="text-sm font-semibold tracking-wide text-white">
                          PERSONAL BASELINE ESTABLISHED
                        </h2>
                        <p className="text-xs text-[#8ca49c]">
                          Bilateral references aligned and ready for longitudinal surveillance.
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-6 text-xs text-[#9eb5ae]">
                      <div>
                        <span className="block text-[10px] uppercase text-[#617c74]">Observations</span>
                        <strong className="text-white">{demo.baseline.observations} / 28 Qualified</strong>
                      </div>
                      <div>
                        <span className="block text-[10px] uppercase text-[#617c74]">Simulated Span</span>
                        <strong className="text-white">{demo.baseline.span_days.toFixed(1)} Days</strong>
                      </div>
                      <div>
                        <span className="block text-[10px] uppercase text-[#617c74]">Feature Model</span>
                        <strong className="text-white">bis-features-v1</strong>
                      </div>
                      <div>
                        <span className="block text-[10px] uppercase text-[#617c74]">Baseline Revision</span>
                        <strong className="text-white">baseline-v1</strong>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* ========================================================================= */}
        {/* ACT 2 — WATCH AEQUOR REASON (HERO OF COMPETITION) */}
        {/* ========================================================================= */}
        {activeAct === 2 && (
          <section className="animate-fadeIn space-y-6">
            {/* Act 2 Subheader & Checkpoint Bar */}
            <div className="flex flex-col justify-between gap-4 rounded-2xl border border-white/[0.08] bg-[#091a17] p-5 lg:flex-row lg:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-[#62c9b4]/20 px-2.5 py-0.5 text-[10px] font-bold text-[#7fe0cc]">
                    ACT 2 / 3
                  </span>
                  <h1 className="text-lg font-light tracking-wide text-white sm:text-xl">
                    WATCH AEQUOR REASON: SLOW UNILATERAL LEFT
                  </h1>
                </div>
                <p className="mt-1 text-xs text-[#8fa7a0]">
                  Observe what the simulator knows versus what Aequor independently discovers across checkpoints.
                </p>
              </div>

              {/* Checkpoint Controls */}
              <div className="flex flex-wrap items-center gap-3">
                {currentCheckpoint === 0 && (
                  <button
                    onClick={() => void executeDemoAction("start-slow-left")}
                    disabled={!baselineReady || !!runningAction}
                    className="rounded-full bg-[#d6b570] px-5 py-2.5 text-xs font-bold tracking-wider text-[#141208] shadow-[0_6px_20px_rgba(214,181,112,0.25)] hover:bg-[#e4c585] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    START SLOW LEFT EXPERIMENT
                  </button>
                )}

                {currentCheckpoint > 0 && currentCheckpoint < totalCheckpoints && (
                  <button
                    onClick={() => void executeDemoAction("checkpoint")}
                    disabled={!!runningAction}
                    className="group flex items-center gap-2 rounded-full bg-[#62c9b4] px-6 py-2.5 text-xs font-bold tracking-wider text-[#051310] shadow-[0_6px_20px_rgba(98,201,180,0.3)] hover:bg-[#7fe0cc] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <span>
                      {runningAction === "checkpoint"
                        ? "RUNNING CHECKPOINT…"
                        : `RUN NEXT CHECKPOINT (${currentCheckpoint + 1} OF ${totalCheckpoints}) →`}
                    </span>
                  </button>
                )}

                {currentCheckpoint >= totalCheckpoints && (
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-[#62c9b4]/20 px-3 py-1.5 text-xs font-bold text-[#7fe0cc]">
                      ALL 3 CHECKPOINTS COMPLETE ✓
                    </span>
                    <button
                      onClick={() => setActiveAct(3)}
                      className="rounded-full bg-white px-5 py-2 text-xs font-bold tracking-wider text-[#051310] hover:bg-[#e0ede8]"
                    >
                      PROCEED TO ACT 3 →
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Checkpoint Sequence Indicator */}
            <div className="grid grid-cols-3 gap-3">
              <CheckpointPill
                checkpointNumber={1}
                title="DAY 2"
                timeSpan="Day 0 → Day 2"
                active={currentCheckpoint === 1}
                done={currentCheckpoint >= 1}
              />
              <CheckpointPill
                checkpointNumber={2}
                title="DAY 4"
                timeSpan="Day 2 → Day 4"
                active={currentCheckpoint === 2}
                done={currentCheckpoint >= 2}
              />
              <CheckpointPill
                checkpointNumber={3}
                title="DAY 6"
                timeSpan="Day 4 → Day 6"
                active={currentCheckpoint === 3}
                done={currentCheckpoint >= 3}
              />
            </div>

            {/* MAIN 3-PART HERO LAYOUT */}
            <div className="grid gap-6 xl:grid-cols-[1fr_1.1fr_1fr]">
              {/* LEFT: SYNTHETIC GROUND TRUTH */}
              <div className="flex flex-col justify-between rounded-3xl border border-[#d6b570]/25 bg-[#121612] p-6">
                <div>
                  <div className="flex items-center justify-between">
                    <div className="inline-flex items-center gap-1.5 rounded-full border border-[#d6b570]/30 bg-[#d6b570]/10 px-2.5 py-0.5 text-[9px] font-bold tracking-widest text-[#d6b570]">
                      ENGINEERING ONLY
                    </div>
                    <span className="text-[10px] text-[#82887a]">SIMULATOR TRUTH</span>
                  </div>
                  <h2 className="mt-3 text-lg font-light text-[#f0e8d0]">
                    SYNTHETIC DIGITAL-TWIN GROUND TRUTH
                  </h2>
                  <p className="mt-1 text-xs text-[#9d9c8f]">
                    The digital twin scenario modifies hidden simulated physiology only.
                  </p>

                  {/* Visual Divergence of Arms */}
                  <div className="mt-6 rounded-2xl border border-white/[0.06] bg-black/25 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-[#d6b570]">
                      Synthetic Bilateral State
                    </p>
                    <div className="mt-4 grid grid-cols-2 gap-4">
                      {/* Left Arm (Diverging) */}
                      <div className="rounded-xl border border-[#d6b570]/30 bg-[#212015] p-3 text-center">
                        <span className="text-[10px] font-bold text-[#d6b570]">LEFT ARM</span>
                        <div className="mt-2 text-xl font-light text-[#f5ebd2]">
                          +{progressionPct.toFixed(0)}%
                        </div>
                        <p className="mt-1 text-[9px] text-[#a7a28e]">Synthetic shift</p>
                        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-black/40">
                          <div
                            className="h-full rounded-full bg-[#d6b570] transition-all duration-700"
                            style={{ width: `${Math.min(100, Math.max(8, progressionPct))}%` }}
                          />
                        </div>
                      </div>

                      {/* Right Arm (Stable) */}
                      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 text-center">
                        <span className="text-[10px] font-bold text-[#8fa59e]">RIGHT ARM</span>
                        <div className="mt-2 text-xl font-light text-[#cfded9]">0.0%</div>
                        <p className="mt-1 text-[9px] text-[#71857f]">Physiological baseline</p>
                        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-black/40">
                          <div className="h-full w-[8%] rounded-full bg-[#62c9b4]" />
                        </div>
                      </div>
                    </div>
                  </div>

                  <dl className="mt-6 space-y-2.5 text-xs">
                    <Row
                      label="Scenario"
                      value={String(groundTruth.scenario_type ?? "BASELINE_STABLE").replaceAll("_", " ")}
                      highlight
                    />
                    <Row label="Configured side" value={String(groundTruth.affected_arm ?? "NONE")} highlight />
                    <Row label="Synthetic progression" value={`${progressionPct.toFixed(1)}%`} highlight />
                    <Row
                      label="Simulated day"
                      value={`Day ${(currentCheckpoint * 2).toFixed(1)}`}
                      highlight
                    />
                  </dl>
                </div>

                <div className="mt-6 rounded-xl border border-[#d6b570]/20 bg-[#1b1c15] p-3 text-[10px] leading-relaxed text-[#c0ba9e]">
                  ⚠️ <strong>Disclaimer:</strong> Scenario progression is an engineering variable, not disease severity or clinical stage.
                </div>
              </div>

              {/* CENTER: INTELLIGENCE FIREWALL & LIVE PIPELINE */}
              <div className="flex flex-col justify-between rounded-3xl border border-[#62c9b4]/20 bg-[#081714] p-6">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="rounded-full bg-[#62c9b4]/10 px-2.5 py-0.5 text-[9px] font-bold text-[#7fe0cc]">
                      INTELLIGENCE BOUNDARY
                    </span>
                    <span className="text-[10px] text-[#69887e]">FIREWALL ARCHITECTURE</span>
                  </div>

                  {/* Firewall Diagram */}
                  <div className="mt-4 rounded-2xl border border-white/[0.08] bg-black/30 p-4 text-center">
                    <div className="inline-block rounded-lg border border-[#d6b570]/30 bg-[#252216] px-3 py-1 text-[10px] font-bold text-[#d6b570]">
                      SCENARIO LABEL
                    </div>
                    <div className="my-1 text-[#e87060] font-bold text-xs">│<br />✕<br />│<br />✕<br />↓</div>
                    <div className="inline-block rounded-lg border border-[#62c9b4]/30 bg-[#0c2b24] px-3 py-1 text-[10px] font-bold text-[#62c9b4]">
                      AEQUOR INTELLIGENCE
                    </div>
                    <p className="mt-3 text-[10px] font-medium text-[#7d9b91]">
                      SCENARIO IDENTITY IS NOT PROVIDED TO THE INTELLIGENCE PIPELINE.
                    </p>
                  </div>

                  {/* Micro-Principle Line */}
                  <div className="mt-4 rounded-xl border border-white/[0.05] bg-white/[0.02] p-2.5 text-center text-[10px] font-semibold tracking-wider text-[#82a398]">
                    THE DEMO CONTROLS THE EXPERIMENT. THE PIPELINE PRODUCES THE RESULT.
                  </div>

                  {/* STAGED PIPELINE VISUALIZER */}
                  <div className="mt-6">
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] font-bold tracking-wider text-[#a2beb6]">
                        LIVE PIPELINE EXECUTION
                      </p>
                      {pipelineActive && (
                        <span className="animate-pulse text-[10px] font-bold text-[#62c9b4]">
                          PROCESSING…
                        </span>
                      )}
                    </div>

                    <div className="mt-3 space-y-1.5">
                      {pipelineState.map((step) => (
                        <div
                          key={step.id}
                          className={`flex items-center justify-between rounded-xl px-3 py-2 text-xs transition-colors ${
                            step.status === "RUNNING"
                              ? "border border-[#62c9b4]/50 bg-[#62c9b4]/15 text-white"
                              : step.status === "COMPLETED"
                              ? "bg-white/[0.03] text-[#cfded9]"
                              : step.status === "REJECTED"
                              ? "border border-[#e87060]/50 bg-[#e87060]/15 text-[#ffaba0]"
                              : step.status === "BLOCKED"
                              ? "bg-white/[0.015] text-[#71857f] opacity-50"
                              : "bg-transparent text-[#5c756e] opacity-40"
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono text-[10px] font-bold uppercase">{step.label}</span>
                            <span className="text-[10px] text-[#739188]">{step.sublabel}</span>
                          </div>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${
                              step.status === "COMPLETED"
                                ? "bg-[#62c9b4]/20 text-[#7fe0cc]"
                                : step.status === "RUNNING"
                                ? "animate-pulse bg-[#62c9b4] text-[#051310]"
                                : step.status === "REJECTED"
                                ? "bg-[#e87060]/20 text-[#ffaba0]"
                                : step.status === "BLOCKED"
                                ? "bg-white/10 text-[#8ea39c]"
                                : "text-[#5c756e]"
                            }`}
                          >
                            {step.status}
                          </span>
                        </div>
                      ))}
                    </div>

                    {pipelineMessage && (
                      <p
                        className={`mt-3 text-center text-xs font-semibold ${
                          pipelineRejected ? "text-[#e87060]" : "text-[#62c9b4]"
                        }`}
                      >
                        {pipelineMessage}
                      </p>
                    )}
                  </div>
                </div>

                <p className="mt-6 text-center text-[10px] text-[#69887e]">
                  Local INT8 TinyML inference · Zero external cloud dependency
                </p>
              </div>

              {/* RIGHT: AEQUOR OBSERVED EVIDENCE */}
              <div className="flex flex-col justify-between rounded-3xl border border-[#62c9b4]/25 bg-[#091a17] p-6">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="rounded-full border border-[#62c9b4]/30 bg-[#62c9b4]/10 px-2.5 py-0.5 text-[9px] font-bold tracking-widest text-[#7fe0cc]">
                      REAL AI PIPELINE
                    </span>
                    <span className="text-[10px] text-[#729188]">OBSERVED EVIDENCE</span>
                  </div>
                  <h2 className="mt-3 text-lg font-light text-white">
                    AEQUOR OBSERVED EVIDENCE
                  </h2>
                  <p className="mt-1 text-xs text-[#8fa7a0]">
                    Only authoritative values produced by the real execution cycle.
                  </p>

                  {/* Surveillance State Morphing Badge */}
                  <div className="mt-6 rounded-2xl border border-white/[0.08] bg-black/25 p-4 text-center">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#79998f]">
                      Surveillance State
                    </span>
                    <div className="mt-2 flex items-center justify-center">
                      <StateBadge state={observed?.surveillance_state ?? "WITHIN_PERSONAL_BASELINE"} />
                    </div>
                  </div>

                  {/* ADI Hero Index */}
                  <div className="mt-4 rounded-2xl border border-[#62c9b4]/20 bg-[#0d2722] p-4 text-center">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#7fe0cc]">
                      AEQUOR DIFFERENTIAL INDEX (ADI)
                    </span>
                    <div className="mt-2 text-4xl font-light text-white sm:text-5xl">
                      {displayAdi != null ? displayAdi.toFixed(1) : "—"}
                      <span className="text-xl text-[#7fe0cc]"> / 100</span>
                    </div>
                    <p className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-[#6cb5a5]">
                      PROTOTYPE RESEARCH INDEX · NOT DISEASE PROBABILITY
                    </p>
                  </div>

                  {/* Observed Metrics Grid */}
                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <MetricCard
                      label="OBSERVED DOMINANT SIDE"
                      value={observed?.dominant_observed_side ?? "UNDETERMINED"}
                    />
                    <MetricCard
                      label="PATTERN NOVELTY (Z)"
                      value={displayNovelty != null ? displayNovelty.toFixed(2) : "—"}
                    />
                    <MetricCard
                      label="PERSISTENCE"
                      value={`${displayPersistence != null ? displayPersistence.toFixed(1) : "0.0"} days`}
                    />
                    <MetricCard
                      label="SYSTEMIC EVIDENCE"
                      value={observed?.systemic_label ?? "LOW"}
                    />
                  </div>

                  <div className="mt-3 rounded-xl bg-white/[0.025] p-3 text-[11px] text-[#8fa7a0]">
                    <span className="text-[9px] uppercase tracking-wider text-[#627d75]">Deviation summary: </span>
                    <strong className="text-white">
                      {observed?.personal_deviation_summary ?? "Pending observation"}
                    </strong>
                  </div>
                </div>

                <div className="mt-6 border-t border-white/[0.08] pt-3 text-center text-[10px] text-[#69887e]">
                  Cycle Index: #{observed?.cycle_index ?? 0} · Quality: {observed?.quality ?? "READY"}
                </div>
              </div>
            </div>

            {/* SYNCHRONIZED 3-PANEL STORY CHART */}
            <div className="rounded-3xl border border-white/[0.08] bg-[#071714] p-6">
              <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-[#7fe0cc]">
                    SYNCHRONIZED LONGITUDINAL STORY
                  </p>
                  <h3 className="mt-1 text-xl font-light text-white">
                    What Changed Over Simulated Time
                  </h3>
                </div>
                <span className="rounded-full bg-white/[0.04] px-3 py-1 text-xs text-[#8ca49c]">
                  {demo?.trend.length ?? 0} Qualified Observations
                </span>
              </div>

              <div className="mt-6 grid gap-4 lg:grid-cols-3">
                {/* Panel A: Bilateral Pattern */}
                <ChartPanel
                  title="Panel A · Bilateral Pattern"
                  subtitle="LEFT vs RIGHT relative index"
                  legend="LEFT (teal) / RIGHT (gold)"
                  series={[
                    demo?.trend.map((x) => x.left_relative_pattern) ?? [],
                    demo?.trend.map((x) => x.right_relative_pattern) ?? [],
                  ]}
                  colors={["#62c9b4", "#d6b570"]}
                />

                {/* Panel B: AI / Temporal Evidence */}
                <ChartPanel
                  title="Panel B · AI / Temporal Evidence"
                  subtitle="Novelty Z & EWMA accumulation"
                  legend="NOVELTY Z (blue) / EWMA (purple)"
                  series={[
                    demo?.trend.map((x) => x.novelty_z) ?? [],
                    demo?.trend.map((x) => x.ewma) ?? [],
                  ]}
                  colors={["#7fc2e8", "#bb9fe0"]}
                />

                {/* Panel C: Decision & State Bands */}
                <ChartPanel
                  title="Panel C · Decision & Thresholds"
                  subtitle="Aequor Differential Index (ADI)"
                  legend="ADI (coral) with state zones"
                  series={[demo?.trend.map((x) => x.adi) ?? []]}
                  colors={["#e89578"]}
                  thresholds={[40, 60, 75]}
                />
              </div>

              <p className="mt-4 text-center text-[10px] text-[#69887e]">
                Synchronized simulated days along x-axis · Inspect how physical divergence drives novelty, then persistence, then ADI
              </p>
            </div>

            {/* PATIENT / CLINICIAN REVEAL ("SAME EVIDENCE. TWO EXPERIENCES.") */}
            <div className="mt-8 rounded-3xl border border-white/[0.08] bg-[#081a16] p-6 sm:p-8">
              <div className="text-center">
                <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[10px] font-bold tracking-widest text-[#8ea39c]">
                  HUMAN-CENTERED CLINICAL TRANSLATION
                </span>
                <h2 className="mt-3 text-2xl font-light text-white sm:text-3xl">
                  SAME EVIDENCE. TWO EXPERIENCES.
                </h2>
                <p className="mx-auto mt-2 max-w-xl text-xs text-[#8ca49c]">
                  Aequor separates calming, non-alarming patient guidance from deep, unvarnished clinical reasoning.
                </p>
              </div>

              <div className="mt-8 grid gap-6 md:grid-cols-2">
                {/* Patient Preview Card */}
                <div className="flex flex-col justify-between rounded-2xl border border-white/10 bg-[#0d221e] p-6 shadow-sm">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="rounded-full bg-[#62c9b4]/15 px-2.5 py-0.5 text-[10px] font-bold text-[#7fe0cc]">
                        PATIENT EXPERIENCE
                      </span>
                      <span className="text-[10px] text-[#78968e]">Calm & Non-alarmist</span>
                    </div>
                    <h3 className="mt-4 text-xl font-light text-white">
                      {demo?.patient_preview?.state_title ?? "Monitoring Maya's personal reference"}
                    </h3>
                    <p className="mt-3 text-xs leading-relaxed text-[#a2beb6]">
                      {demo?.patient_preview?.state_message ??
                        "Your bilateral pattern is being evaluated against your personal reference."}
                    </p>
                    <div className="mt-4 rounded-xl bg-black/20 p-3 text-xs text-[#7fe0cc]">
                      💬 {demo?.patient_preview?.recommended_message ?? "Continue your regular daily check-in routine."}
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-white/[0.06]">
                    <a
                      href="/patient"
                      className="inline-flex items-center gap-2 text-xs font-semibold text-[#62c9b4] hover:text-[#7fe0cc]"
                    >
                      OPEN PATIENT EXPERIENCE →
                    </a>
                  </div>
                </div>

                {/* Clinician Preview Card */}
                <div className="flex flex-col justify-between rounded-2xl border border-[#d6b570]/20 bg-[#171e1b] p-6 shadow-sm">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="rounded-full bg-[#d6b570]/15 px-2.5 py-0.5 text-[10px] font-bold text-[#d6b570]">
                        CLINICIAN EVIDENCE
                      </span>
                      <span className="text-[10px] text-[#939282]">Full Analytical Trace</span>
                    </div>
                    <div className="mt-4 flex items-baseline justify-between">
                      <div>
                        <span className="text-[10px] uppercase text-[#7a8a83]">State: </span>
                        <strong className="text-sm font-semibold text-white">
                          {demo?.clinician_preview?.surveillance_state?.replaceAll("_", " ") ?? "CALIBRATING"}
                        </strong>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] uppercase text-[#7a8a83]">ADI: </span>
                        <strong className="text-lg font-light text-[#d6b570]">
                          {demo?.clinician_preview?.adi != null ? Number(demo.clinician_preview.adi).toFixed(1) : "—"}
                          <span className="text-xs"> / 100</span>
                        </strong>
                      </div>
                    </div>

                    <dl className="mt-4 space-y-2 text-xs">
                      <Row
                        label="Observed dominant side"
                        value={demo?.clinician_preview?.dominant_observed_side ?? "Undetermined"}
                      />
                      <Row
                        label="Persistence"
                        value={`${demo?.clinician_preview?.temporal_summary?.persistence_duration_days?.toFixed(1) ?? "0.0"} days`}
                      />
                      <Row
                        label="Technical quality score"
                        value={`${demo?.clinician_preview?.quality_summary?.latest_score?.toFixed(0) ?? "—"} / 100`}
                      />
                    </dl>
                  </div>

                  <div className="mt-6 pt-4 border-t border-white/[0.06] flex items-center justify-between">
                    <a
                      href="/clinician"
                      className="inline-flex items-center gap-2 text-xs font-semibold text-[#d6b570] hover:text-[#e4c585]"
                    >
                      OPEN CLINICIAN EVIDENCE →
                    </a>
                    <span className="text-[9px] text-[#71857e]">Prototype research index</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ========================================================================= */}
        {/* ACT 3 — TRY TO FOOL AEQUOR (EMBEDDED ROBUSTNESS TESTS) */}
        {/* ========================================================================= */}
        {activeAct === 3 && (
          <section className="animate-fadeIn space-y-6">
            <div className="flex flex-col justify-between gap-4 rounded-2xl border border-white/[0.08] bg-[#091a17] p-5 lg:flex-row lg:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-[#d6b570]/20 px-2.5 py-0.5 text-[10px] font-bold text-[#d6b570]">
                    ACT 3 / 3
                  </span>
                  <h1 className="text-lg font-light tracking-wide text-white sm:text-xl">
                    TRY TO FOOL AEQUOR: ADVERSARIAL STRESS TESTS
                  </h1>
                </div>
                <p className="mt-1 text-xs text-[#8fa7a0]">
                  Stress-test quality rejection, bilateral systemic differentiation, and transient spike resilience directly inside the demo.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => void runAllChallenges()}
                  disabled={!!runningAction}
                  className="rounded-full bg-[#62c9b4] px-6 py-2.5 text-xs font-bold tracking-wider text-[#051310] hover:bg-[#7fe0cc] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {runningAction === "all-challenges" ? "RUNNING ALL 10 TESTS…" : "RUN FULL ADVERSARIAL SUITE (10/10)"}
                </button>
              </div>
            </div>

            {/* Suite Summary Banner if Run */}
            {suiteSummary && (
              <div className="rounded-2xl border border-[#62c9b4]/30 bg-[#0c2420] p-4 text-center">
                <p className="text-sm font-semibold text-white">
                  <span className="text-[#62c9b4]">{suiteSummary.passed} / {suiteSummary.total}</span>{" "}
                  ENGINEERING ROBUSTNESS CHECKS PASSED
                </p>
                <p className="mt-1 text-[11px] text-[#8fa7a0]">
                  Controlled synthetic engineering verification. Not clinical accuracy, sensitivity, specificity, or diagnostic performance.
                </p>
              </div>
            )}

            {/* THREE HERO EMBEDDED CHALLENGE CARDS */}
            <div className="grid gap-6 md:grid-cols-3">
              {/* Challenge 1: Active Motion */}
              <ChallengeCard
                title="CAN MOVEMENT FOOL AEQUOR?"
                condition="Active Motion"
                question="Can patient motion create a false physiological signal?"
                result={challengeResults["active-motion"]}
                onRun={() => void runChallenge("active-motion")}
                running={runningAction === "active-motion"}
                badge="STAGE 4 GATING"
              >
                <div className="mt-3 rounded-xl bg-black/25 p-3 text-[11px] text-[#8fa7a0]">
                  <p className="font-semibold text-white">Expected Pipeline Behavior:</p>
                  <p className="mt-1 text-[10px]">
                    Quality rejects the cycle immediately before BIS, ML, temporal, or decision.
                  </p>
                </div>
              </ChallengeCard>

              {/* Challenge 2: Systemic Bilateral */}
              <ChallengeCard
                title="WHAT IF BOTH ARMS CHANGE?"
                condition="Systemic Bilateral Shift"
                question="Can a bilateral systemic-style change look like unilateral progression?"
                result={challengeResults["systemic-shift"]}
                onRun={() => void runChallenge("systemic-shift")}
                running={runningAction === "systemic-shift"}
                badge="CONFOUNDER REASONING"
              >
                <div className="mt-3 rounded-xl bg-black/25 p-3 text-[11px] text-[#8fa7a0]">
                  <p className="font-semibold text-white">Expected Pipeline Behavior:</p>
                  <p className="mt-1 text-[10px]">
                    Bilateral coherence score elevates; systemic evidence suppresses false unilateral alarm.
                  </p>
                </div>
              </ChallengeCard>

              {/* Challenge 3: Transient Spike */}
              <ChallengeCard
                title="CAN ONE SPIKE TRIGGER AN ALERT?"
                condition="Transient Spike Artifact"
                question="Does one isolated large observation trigger a persistent alert?"
                result={challengeResults["transient-spike"]}
                onRun={() => void runChallenge("transient-spike")}
                running={runningAction === "transient-spike"}
                badge="LONGITUDINAL MEMORY"
              >
                <div className="mt-3 rounded-xl bg-black/25 p-3 text-[11px] text-[#8fa7a0]">
                  <p className="font-semibold text-white">Expected Pipeline Behavior:</p>
                  <p className="mt-1 text-[10px]">
                    Instant novelty rises briefly, but persistence and CUSUM prevent entering Persistent Deviation.
                  </p>
                </div>
              </ChallengeCard>
            </div>
          </section>
        )}

        {/* ========================================================================= */}
        {/* FINAL CLOSING FRAME */}
        {/* ========================================================================= */}
        <section className="mt-16 rounded-[2.5rem] border border-white/[0.08] bg-gradient-to-b from-[#081815] to-[#040e0c] p-8 text-center sm:p-14">
          <div className="mx-auto max-w-3xl">
            <span className="text-xs font-black tracking-[0.3em] text-[#62c9b4]">
              AEQUOR
            </span>
            <div className="mt-4 flex flex-wrap justify-center gap-3 text-xs font-semibold tracking-wider text-[#a0bcb4]">
              <span>PERSONALIZED</span> · <span>QUALITY-AWARE</span> · <span>LOCAL EDGE AI</span> · <span>LONGITUDINAL</span> · <span>EXPLAINABLE</span>
            </div>
            <h2 className="mt-6 text-2xl font-light text-white sm:text-4xl">
              SIMULATED SENSING. REAL EXECUTABLE INTELLIGENCE PIPELINE.
            </h2>
            <p className="mt-4 text-xs leading-relaxed text-[#7c9990] sm:text-sm">
              The entire intelligence stack runs locally on-device: from physical multi-frequency Cole bioimpedance gating
              to INT8 quantized autoencoders and temporal confounder suppression.
            </p>
          </div>

          <div className="mt-10 grid gap-6 text-left sm:grid-cols-2">
            <div className="rounded-2xl border border-[#d6b570]/20 bg-[#161a15] p-6">
              <span className="text-[10px] font-bold tracking-widest text-[#d6b570]">SIMULATED</span>
              <h3 className="mt-2 text-sm font-semibold text-white">Synthetic Environment</h3>
              <ul className="mt-3 space-y-1.5 text-xs text-[#a0a599]">
                <li>• Multi-frequency Cole bioimpedance tissue physics</li>
                <li>• Wearable sensor window (virtual IMU & temperature)</li>
                <li>• Electrode contact degradation & motion artifact injection</li>
              </ul>
            </div>

            <div className="rounded-2xl border border-[#62c9b4]/20 bg-[#09211c] p-6">
              <span className="text-[10px] font-bold tracking-widest text-[#62c9b4]">REAL EXECUTABLE SOFTWARE</span>
              <h3 className="mt-2 text-sm font-semibold text-white">Edge Surveillance Pipeline</h3>
              <ul className="mt-3 space-y-1.5 text-xs text-[#9ebcb3]">
                <li>• Technical quality gating & motion rejection</li>
                <li>• Signal processing & personalized baseline calibration</li>
                <li>• INT8 TFLite TinyML autoencoder inference</li>
                <li>• Temporal EWMA, CUSUM & confounder context engine</li>
                <li>• Aequor Differential Index (ADI) & surveillance state machine</li>
              </ul>
            </div>
          </div>

          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <a
              href="/patient"
              className="rounded-full border border-white/15 bg-white/[0.04] px-6 py-3 text-xs font-bold tracking-wider text-white transition hover:bg-white/10"
            >
              PATIENT EXPERIENCE
            </a>
            <a
              href="/clinician"
              className="rounded-full border border-white/15 bg-white/[0.04] px-6 py-3 text-xs font-bold tracking-wider text-white transition hover:bg-white/10"
            >
              CLINICIAN EVIDENCE
            </a>
            <a
              href="/engineering"
              className="rounded-full border border-white/15 bg-white/[0.04] px-6 py-3 text-xs font-bold tracking-wider text-white transition hover:bg-white/10"
            >
              ENGINEERING CONSOLE
            </a>
          </div>

          <p className="mt-8 text-[10px] text-[#556e66]">
            Prototype research platform · Not approved by FDA · For competition and demonstration evaluation only
          </p>
        </section>
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// SUBCOMPONENTS
// ---------------------------------------------------------------------------

function ActTab({
  actNumber,
  title,
  active,
  completed,
  onClick,
}: {
  actNumber: number;
  title: string;
  active: boolean;
  completed: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold tracking-wider transition ${
        active
          ? "bg-[#62c9b4]/15 text-[#7fe0cc] shadow-[inset_0_0_0_1px_rgba(98,201,180,0.3)]"
          : "text-[#708a82] hover:bg-white/[0.04] hover:text-[#a2beb6]"
      }`}
    >
      <span
        className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold ${
          completed
            ? "bg-[#62c9b4] text-[#051310]"
            : active
            ? "border border-[#62c9b4] text-[#62c9b4]"
            : "bg-white/10 text-[#708a82]"
        }`}
      >
        {completed ? "✓" : actNumber}
      </span>
      <span>{title}</span>
    </button>
  );
}

function ProgressPill({ step, label, active }: { step: string; label: string; active: boolean }) {
  return (
    <div
      className={`rounded-xl border p-2.5 text-left text-xs ${
        active ? "border-[#62c9b4]/40 bg-[#62c9b4]/10 text-white" : "border-white/10 bg-white/[0.02] text-[#68827a]"
      }`}
    >
      <span className="block text-[9px] font-bold uppercase text-[#62c9b4]">Step {step}</span>
      <span className="mt-1 block font-medium">{label}</span>
    </div>
  );
}

function BilateralArmCard({
  side,
  status,
  value,
  subtext,
  calibrated,
}: {
  side: string;
  status: string;
  value: string;
  subtext: string;
  calibrated: boolean;
}) {
  return (
    <div
      className={`rounded-2xl border p-6 text-center transition-all ${
        calibrated ? "border-[#62c9b4]/30 bg-[#0a231e]" : "border-white/10 bg-[#091a17]"
      }`}
    >
      <span className="text-[10px] font-bold uppercase tracking-widest text-[#79998f]">{side}</span>
      <div className="my-6 flex justify-center">
        <div
          className={`relative flex h-28 w-28 items-center justify-center rounded-full border-2 ${
            calibrated
              ? "border-[#62c9b4] bg-[#62c9b4]/10 shadow-[0_0_25px_rgba(98,201,180,0.2)]"
              : "animate-pulse border-white/20 bg-white/[0.02]"
          }`}
        >
          <span className="text-3xl font-light text-white">{value}</span>
        </div>
      </div>
      <p className="text-xs font-semibold text-white">{status}</p>
      <p className="mt-1 text-[11px] text-[#718c84]">{subtext}</p>
    </div>
  );
}

function CheckpointPill({
  checkpointNumber,
  title,
  timeSpan,
  active,
  done,
}: {
  checkpointNumber: number;
  title: string;
  timeSpan: string;
  active: boolean;
  done: boolean;
}) {
  return (
    <div
      className={`rounded-2xl border p-3.5 text-center transition-all ${
        active
          ? "border-[#62c9b4] bg-[#62c9b4]/15 text-white shadow-[0_0_15px_rgba(98,201,180,0.2)]"
          : done
          ? "border-[#62c9b4]/30 bg-[#09211c] text-[#a0c2b9]"
          : "border-white/[0.06] bg-white/[0.02] text-[#5e7770]"
      }`}
    >
      <span className="block text-[9px] font-bold uppercase tracking-widest text-[#62c9b4]">
        CHECKPOINT {checkpointNumber} OF 3
      </span>
      <strong className="mt-1 block text-sm font-semibold">{title}</strong>
      <span className="mt-0.5 block text-[10px] opacity-80">{timeSpan}</span>
    </div>
  );
}

function Row({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between border-b border-white/[0.04] pb-1.5">
      <span className="text-[#879992]">{label}</span>
      <strong className={highlight ? "font-semibold text-white" : "text-[#d6b570]"}>{value}</strong>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/[0.05] bg-white/[0.02] p-3 text-center">
      <span className="text-[9px] uppercase tracking-wider text-[#69887e]">{label}</span>
      <div className="mt-1 text-sm font-semibold text-white">{value}</div>
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const s = state.toUpperCase();
  let badgeStyle = "border-[#62c9b4]/40 bg-[#62c9b4]/15 text-[#7fe0cc]";
  if (s.includes("OBSERVING")) {
    badgeStyle = "border-[#d6b570]/40 bg-[#d6b570]/15 text-[#e5c98a]";
  } else if (s.includes("PERSISTENT")) {
    badgeStyle = "border-[#e89578]/40 bg-[#e89578]/15 text-[#ffa88f]";
  } else if (s.includes("CLINICAL")) {
    badgeStyle = "border-[#e87060]/40 bg-[#e87060]/15 text-[#ffaba0]";
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-4 py-1.5 text-xs font-bold tracking-wider ${badgeStyle}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {s.replaceAll("_", " ")}
    </span>
  );
}

function ChartPanel({
  title,
  subtitle,
  legend,
  series,
  colors,
  thresholds,
}: {
  title: string;
  subtitle: string;
  legend: string;
  series: (number | null)[][];
  colors: string[];
  thresholds?: number[];
}) {
  const allVals = series.flatMap((x) => x).filter((x): x is number => x != null);
  const minVal = Math.min(...(allVals.length ? allVals : [0]), 0);
  const maxVal = Math.max(...(allVals.length ? allVals : [100]), 100);

  const getPoints = (xs: (number | null)[]) => {
    return xs
      .map((v, i) => {
        if (v == null) return null;
        const x = 5 + i * (90 / Math.max(1, xs.length - 1));
        const y = 52 - ((v - minVal) / (maxVal - minVal || 1)) * 44;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ");
  };

  const chartId = useId();

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-black/25 p-4">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="text-xs font-semibold text-white">{title}</h4>
          <p className="text-[10px] text-[#718c84]">{subtitle}</p>
        </div>
        <span className="text-[9px] font-mono text-[#8fa7a0]">{legend}</span>
      </div>

      <div className="relative mt-3 h-32 w-full">
        {allVals.length > 0 ? (
          <svg viewBox="0 0 100 60" className="h-full w-full" aria-labelledby={chartId}>
            <title id={chartId}>{`${title}: synchronized longitudinal demo trend`}</title>
            {/* Grid baseline */}
            <line x1="4" y1="53" x2="96" y2="53" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line x1="4" y1="8" x2="96" y2="8" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />

            {/* Threshold lines if provided */}
            {thresholds?.map((t) => {
              const y = 52 - ((t - minVal) / (maxVal - minVal || 1)) * 44;
              return (
                <line
                  key={t}
                  x1="4"
                  y1={y}
                  x2="96"
                  y2={y}
                  stroke="rgba(232, 149, 120, 0.25)"
                  strokeWidth="0.5"
                  strokeDasharray="2 2"
                />
              );
            })}

            {/* Render lines */}
            {series.map((line, idx) => (
              <polyline
                key={colors[idx]}
                points={getPoints(line)}
                fill="none"
                stroke={colors[idx]}
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ))}
          </svg>
        ) : (
          <div className="flex h-full items-center justify-center text-[10px] text-[#557068]">
            Trend recorded as checkpoints execute
          </div>
        )}
      </div>
    </div>
  );
}

function ChallengeCard({
  title,
  condition,
  question,
  result,
  onRun,
  running,
  badge,
  children,
}: {
  title: string;
  condition: string;
  question: string;
  result?: ChallengeResult;
  onRun: () => void;
  running: boolean;
  badge: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between rounded-3xl border border-white/10 bg-[#091a17] p-6">
      <div>
        <div className="flex items-center justify-between">
          <span className="rounded-full bg-white/[0.04] px-2.5 py-0.5 text-[9px] font-bold text-[#8ba39c]">
            {badge}
          </span>
          {result ? (
            <span
              className={`rounded-full px-2.5 py-0.5 text-[9px] font-bold ${
                result.status === "PASS"
                  ? "border border-[#62c9b4]/40 bg-[#62c9b4]/15 text-[#7fe0cc]"
                  : "border border-[#e87060]/40 bg-[#e87060]/15 text-[#ffaba0]"
              }`}
            >
              {result.status}
            </span>
          ) : (
            <span className="rounded-full bg-white/[0.03] px-2 py-0.5 text-[9px] text-[#69857d]">NOT TESTED</span>
          )}
        </div>

        <h3 className="mt-3 text-base font-light text-white">{title}</h3>
        <p className="mt-1 text-xs text-[#8ca49c]">{condition}</p>
        <p className="mt-3 text-xs leading-relaxed text-[#adc4bd]">{question}</p>

        {children}

        {result && (
          <div className="mt-4 rounded-xl border border-white/[0.06] bg-black/30 p-3">
            <span className="text-[9px] font-bold uppercase tracking-wider text-[#62c9b4]">
              Authoritative Verdict:
            </span>
            <p className="mt-1 text-xs text-[#b8ccc6]">{result.explanation}</p>
          </div>
        )}
      </div>

      <div className="mt-6 pt-4 border-t border-white/[0.06]">
        <button
          onClick={onRun}
          disabled={running}
          className="w-full rounded-full border border-[#62c9b4]/30 bg-[#62c9b4]/10 py-2.5 text-xs font-bold tracking-wider text-[#7fe0cc] transition hover:bg-[#62c9b4]/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {running ? "TESTING LIVE PIPELINE…" : "RUN TEST"}
        </button>
      </div>
    </div>
  );
}
