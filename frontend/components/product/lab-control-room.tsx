"use client";
import { useCallback, useEffect, useState } from "react";
import { TopNav } from "./engineering-console";
const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type L = {
  simulation: Record<string, unknown>;
  scenario_ground_truth: Record<string, unknown>;
  baseline: Record<string, unknown>;
  runtime: Record<string, unknown>;
  observed_evidence: Record<string, unknown> | null;
  event_feed: { simulated_time: string; event: string; detail: string }[];
  disclosure: string;
};
const PRESETS = [
  { name: "Stable reference", type: "BASELINE_STABLE", side: null },
  { name: "Transient LEFT", type: "TRANSIENT_UNILATERAL_SHIFT", side: "LEFT" },
  { name: "Slow persistent LEFT", type: "SLOW_UNILATERAL_SHIFT", side: "LEFT" },
  {
    name: "Slow persistent RIGHT",
    type: "SLOW_UNILATERAL_SHIFT",
    side: "RIGHT",
  },
  { name: "Systemic bilateral", type: "SYSTEMIC_BILATERAL_SHIFT", side: null },
  { name: "Recovery", type: "RECOVERY", side: "LEFT" },
];
export function LabControlRoom() {
  const [d, setD] = useState<L | null>(null);
  const [error, setError] = useState(false);
  const [condition, setCondition] = useState("STABLE_REST");
  const load = useCallback(
    async () => { try { const response=await fetch(`${api}/api/v1/views/lab`); if(!response.ok)throw new Error(); setD(await response.json()); setError(false) } catch { setError(true) } },
    [],
  );
  const post = async (path: string, body: object = {}) => {
    await fetch(`${api}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    await load();
  };
  useEffect(() => {
    const first = setTimeout(() => void load(), 0);
    const id = setInterval(() => void load(), 5000);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [load]);
  if (error) return <main className="min-h-screen bg-[#081310] p-8 text-white"><b className="text-[#d2aa68]">BACKEND UNAVAILABLE</b><p className="mt-3 text-sm">Lab evidence is hidden until the backend reconnects.</p></main>;
  if (!d)
    return (
      <main className="min-h-screen bg-[#081310] p-8 text-white">
        Preparing Aequor Lab…
      </main>
    );
  const g = d.scenario_ground_truth;
  const o = d.observed_evidence;
  const scenario = String(g.scenario_type ?? "BASELINE_STABLE");
  return (
    <main className="min-h-screen bg-[#081310] text-[#e2eee9]">
      <TopNav active="Aequor Lab" />
      <div className="mx-auto max-w-[1500px] px-5 py-7">
        <header className="rounded-[2rem] border border-[#d2aa68]/20 bg-[#15211c] p-7">
          <p className="text-xs font-semibold tracking-[.24em] text-[#d2aa68]">
            AEQUOR LAB · COMPETITION DEMONSTRATION
          </p>
          <h1 className="mt-3 text-4xl font-light sm:text-5xl">
            Digital-Twin Control Room
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-[#99aaa4]">
            {d.disclosure}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              className="labAction"
              onClick={() => void post("/api/v1/baseline/run-demo-calibration")}
            >
              Establish demo baseline
            </button>
            <button
              className="labAction secondary"
              onClick={() => void post("/api/v1/simulation/reset")}
            >
              Full reset
            </button>
            <button
              className="labAction secondary"
              onClick={() => void post("/api/v1/scenarios/reset")}
            >
              Reset scenario only
            </button>
          </div>
        </header>
        <section className="mt-5 grid gap-5 lg:grid-cols-[1.05fr_.95fr]">
          <div className="rounded-3xl border border-[#d2aa68]/20 bg-[#161f1b] p-6">
            <p className="text-[10px] font-semibold tracking-[.2em] text-[#d2aa68]">
              SYNTHETIC DIGITAL-TWIN GROUND TRUTH
            </p>
            <h2 className="mt-3 text-2xl">The experiment knows the scenario</h2>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <LabMetric
                label="Scenario"
                value={scenario.replaceAll("_", " ")}
              />
              <LabMetric
                label="Configured side"
                value={String(g.affected_arm ?? "BILATERAL / NONE")}
              />
              <LabMetric
                label="Progression"
                value={`${(Number(g.severity ?? 0) * 100).toFixed(0)}%`}
              />
              <LabMetric
                label="Simulated time"
                value={new Date(
                  String(d.simulation.simulated_time),
                ).toLocaleString()}
              />
            </div>
            <div className="mt-5 h-2 rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-[#d2aa68]"
                style={{ width: `${Number(g.severity ?? 0) * 100}%` }}
              />
            </div>
            <p className="mt-3 text-xs text-[#8e9e98]">
              Scenario progression is ground truth. It is not ADI and never
              enters Aequor intelligence.
            </p>
          </div>
          <div className="rounded-3xl border border-[#66bea9]/20 bg-[#0d2420] p-6">
            <p className="text-[10px] font-semibold tracking-[.2em] text-[#66bea9]">
              WHAT AEQUOR OBSERVES
            </p>
            <h2 className="mt-3 text-2xl">Independent observed evidence</h2>
            {o ? (
              <div className="mt-5 grid grid-cols-2 gap-3">
                <LabMetric
                  label="Technical quality"
                  value={String(o.technical_quality)}
                />
                <LabMetric
                  label="Observed side"
                  value={String(o.dominant_observed_side ?? "UNDETERMINED")}
                />
                <LabMetric label="Novelty Z" value={fmt(o.novelty_z)} />
                <LabMetric label="EWMA" value={fmt(o.ewma)} />
                <LabMetric label="CUSUM" value={fmt(o.cusum)} />
                <LabMetric
                  label="Persistence"
                  value={`${fmt(o.persistence_days)} days`}
                />
                <LabMetric
                  label="Systemic evidence"
                  value={fmt(o.systemic_evidence)}
                />
                <LabMetric label="ADI" value={fmt(o.adi)} />
                <div className="col-span-2 rounded-xl bg-white/[.05] p-4">
                  <p className="text-[10px] text-[#79938c]">
                    SURVEILLANCE STATE
                  </p>
                  <p className="mt-1 text-lg">
                    {String(o.surveillance_state).replaceAll("_", " ")}
                  </p>
                </div>
              </div>
            ) : (
              <p className="mt-6 text-sm text-[#849a93]">
                Run an eligible measurement cycle to create observed evidence.
              </p>
            )}
            <p className="mt-5 text-xs text-[#7f9992]">
              Observed outputs are calculated independently from the scenario
              label.
            </p>
          </div>
        </section>
        <section className="mt-5 rounded-3xl border border-white/10 bg-[#0d1d19] p-6">
          <div className="flex flex-col justify-between gap-4 lg:flex-row">
            <div>
              <p className="text-xs font-semibold tracking-[.18em] text-[#91aaa3]">
                JUDGE-FRIENDLY SCENARIOS
              </p>
              <h2 className="mt-2 text-2xl">Choose an experiment</h2>
            </div>
            <p className="text-sm text-[#849a93]">
              Baseline: {String(d.baseline.state)} ·{" "}
              {String(d.baseline.observations)} observations ·{" "}
              {String(d.baseline.span_days)} days
            </p>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {PRESETS.map((p) => (
              <button
                key={p.name}
                onClick={async () => {
                  await post("/api/v1/scenarios/select", {
                    scenario_type: p.type,
                    affected_arm: p.side,
                  });
                  await post("/api/v1/scenarios/start");
                }}
                className={`rounded-2xl border p-4 text-left ${scenario === p.type && String(g.affected_arm ?? "") === String(p.side ?? "") ? "border-[#d2aa68]/60 bg-[#d2aa68]/10" : "border-white/10 bg-white/[.03]"}`}
              >
                <strong className="text-sm">{p.name}</strong>
                <span className="mt-2 block text-xs text-[#7f9992]">
                  {p.type.replaceAll("_", " ")}
                </span>
              </button>
            ))}
          </div>
        </section>
        <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_1fr]">
          <section className="rounded-3xl border border-white/10 bg-[#0d1d19] p-6">
            <h2 className="text-xl">Advance the experiment</h2>
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                className="labAction secondary"
                onClick={() =>
                  void post("/api/v1/simulation/step", { seconds: 21600 })
                }
              >
                +6 hours
              </button>
              <button
                className="labAction secondary"
                onClick={() =>
                  void post("/api/v1/simulation/step", { seconds: 86400 })
                }
              >
                +1 day
              </button>
              <button
                className="labAction secondary"
                onClick={() =>
                  void post("/api/v1/simulation/step", { seconds: 172800 })
                }
              >
                +2 days
              </button>
            </div>
            <p className="mt-7 text-xs font-semibold tracking-[.18em] text-[#91aaa3]">
              SENSOR CONDITION
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {[
                ["Stable / nominal", "STABLE_REST"],
                ["Active motion", "ACTIVE_MOTION"],
                ["Poor contact", "POOR_CONTACT"],
                ["Posture transition", "POSTURE_TRANSITION"],
              ].map(([label, value]) => (
                <button
                  key={value}
                  onClick={() => setCondition(value)}
                  className={`rounded-xl border p-3 text-sm ${condition === value ? "border-[#66bea9] text-[#8fd5c5]" : "border-white/10 text-[#849a93]"}`}
                >
                  {label}
                </button>
              ))}
            </div>
            <button
              className="mt-6 w-full rounded-2xl bg-[#66bea9] px-5 py-4 text-sm font-bold uppercase tracking-wider text-[#09201a]"
              onClick={() =>
                void post("/api/v1/runtime/measure", {
                  motion_condition: condition === "POOR_CONTACT" ? "STABLE_REST" : condition,
                  contact_condition: condition === "POOR_CONTACT" ? "POOR_CONTACT" : "NOMINAL_CONTACT",
                })
              }
            >
              Run measurement cycle
            </button>
            <p className="mt-3 text-center text-xs text-[#7f9992]">
              Uses the integrated Phase-13 runtime; no frontend stage
              orchestration.
            </p>
          </section>
          <section className="rounded-3xl border border-white/10 bg-[#0d1d19] p-6">
            <h2 className="text-xl">Actual event feed</h2>
            <div className="mt-5 max-h-80 space-y-3 overflow-auto">
              {d.event_feed.length ? (
                d.event_feed
                  .slice()
                  .reverse()
                  .map((x, i) => (
                    <div
                      key={`${x.simulated_time}-${i}`}
                      className="border-l border-[#66bea9]/40 pl-4"
                    >
                      <p className="text-sm">{x.event}</p>
                      <p className="mt-1 text-xs text-[#7f9992]">
                        {new Date(x.simulated_time).toLocaleString()} ·{" "}
                        {x.detail}
                      </p>
                    </div>
                  ))
              ) : (
                <p className="text-sm text-[#7f9992]">
                  Events appear after real runtime cycles.
                </p>
              )}
            </div>
          </section>
        </div>
        <section className="mt-5 rounded-3xl border border-white/10 bg-[#0d1d19] p-6">
          <p className="text-xs font-semibold tracking-[.18em] text-[#91aaa3]">
            FAST DEMO SEQUENCE
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[#a4b7b1]">
            {[
              "Establish baseline",
              "Choose slow LEFT",
              "Start",
              "+2 days",
              "Measure",
              "+2 days",
              "Measure",
              "+2 days",
              "Measure",
            ].map((x, i) => (
              <span
                key={`${x}-${i}`}
                className="rounded-full bg-white/[.05] px-3 py-2"
              >
                {i + 1}. {x}
              </span>
            ))}
          </div>
        </section>
      </div>
      <style jsx global>{`
        .labAction {
          border-radius: 999px;
          background: #d2aa68;
          color: #17140d;
          padding: 0.75rem 1rem;
          font-size: 0.7rem;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }
        .labAction.secondary {
          background: transparent;
          color: #a9bbb5;
          border: 1px solid rgba(255, 255, 255, 0.14);
        }
      `}</style>
    </main>
  );
}
function LabMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/[.04] p-3">
      <p className="text-[10px] uppercase tracking-wider text-[#788f88]">
        {label}
      </p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  );
}
function fmt(v: unknown) {
  return v == null ? "—" : Number(v).toFixed(2);
}
