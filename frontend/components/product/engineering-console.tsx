/* eslint-disable @next/next/no-html-link-for-pages */
"use client";
import { useCallback, useEffect, useState } from "react";
const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ws =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
    /^http/,
    "ws",
  ) + "/ws/runtime";
type E = {
  header: Record<string, unknown>;
  pipeline: { stage: string; status: string }[];
  latest_cycle: Record<string, unknown> | null;
  technical_acquisition: Record<string, unknown> | null;
  bis: {
    left: Record<string, number>[];
    right: Record<string, number>[];
  } | null;
  signal_processing: Record<string, unknown> | null;
  baseline: Record<string, unknown>;
  tinyml: Record<string, unknown>;
  temporal: Record<string, unknown> | null;
  temporal_history: Record<string, unknown>[];
  confounders: Record<string, unknown> | null;
  decision: Record<string, unknown> | null;
  adi_configuration: Record<string, unknown>;
  system_health: Record<string, string>;
  provenance: { simulated_inputs: string[]; executable_software: string[] };
};
export function EngineeringConsole() {
  const [d, setD] = useState<E | null>(null);
  const load = useCallback(
    async () =>
      setD(await (await fetch(`${api}/api/v1/views/engineering`)).json()),
    [],
  );
  useEffect(() => {
    const first = setTimeout(() => void load(), 0);
    const socket = new WebSocket(ws);
    socket.onmessage = () => void load();
    const fallback = setInterval(() => void load(), 15000);
    return () => {
      clearTimeout(first);
      clearInterval(fallback);
      socket.close();
    };
  }, [load]);
  const post = async (path: string, body: object = {}) => {
    await fetch(`${api}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    await load();
  };
  if (!d)
    return (
      <main className="min-h-screen bg-[#071313] p-8 text-white">
        Loading engineering console…
      </main>
    );
  const h = d.header;
  const latest = d.latest_cycle;
  const q = d.technical_acquisition;
  const ml = d.tinyml.latest as Record<string, number | string> | null;
  const t = d.temporal;
  const c = d.confounders;
  const dec = d.decision;
  const components = (dec?.components ?? {}) as Record<string, number>;
  const modifiers = (dec?.modifiers ?? {}) as Record<string, number>;
  return (
    <main className="min-h-screen bg-[#071313] text-[#dcebe7]">
      <TopNav active="Engineering" />
      <div className="mx-auto max-w-[1500px] px-5 py-7">
        <header className="flex flex-col justify-between gap-5 border-b border-white/10 pb-6 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-semibold tracking-[.24em] text-[#78c4b3]">
              PROTOTYPE / ENGINEERING
            </p>
            <h1 className="mt-2 text-4xl font-light">
              Aequor Engineering Console
            </h1>
            <p className="mt-2 text-sm text-[#819a94]">
              {String(h.patient)} · simulated{" "}
              {new Date(String(h.simulated_time)).toLocaleString()}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => void post("/api/v1/runtime/measure")}
              className="action"
            >
              Run measurement cycle
            </button>
            <button
              onClick={() => void post("/api/v1/temporal/reset")}
              className="action secondary"
            >
              Temporal reset
            </button>
            <button
              onClick={() => void post("/api/v1/simulation/reset")}
              className="action secondary"
            >
              Full system reset
            </button>
          </div>
        </header>
        <section className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-9">
          {d.pipeline.map((x, i) => (
            <div
              key={x.stage}
              className="relative rounded-2xl border border-white/10 bg-[#0d201e] p-3"
            >
              <p className="text-[10px] tracking-wider text-[#7f9992]">
                {i + 1}. {x.stage}
              </p>
              <p className="mt-2 text-xs font-semibold text-[#b9d2cc]">
                {x.status}
              </p>
            </div>
          ))}
        </section>
        <div className="mt-5 grid gap-5 xl:grid-cols-[.7fr_1.3fr]">
          <Card
            title="Latest cycle"
            eyebrow={latest ? `Cycle ${latest.cycle_index}` : "NOT RUN"}
          >
            {latest ? (
              <div className="space-y-3 text-sm">
                <Line k="Pipeline" v={String(latest.pipeline_status)} />
                <Line k="Quality" v={String(latest.quality_result)} />
                <Line
                  k="Decision updated"
                  v={latest.decision_updated ? "YES" : "NO"}
                />
                <Line
                  k="Current state"
                  v={String(latest.current_surveillance_state)}
                />
                <Line
                  k="Last decision"
                  v={String(latest.last_decision_time ?? "—")}
                />
                {Array.isArray(latest.rejection_codes) &&
                  latest.rejection_codes.length > 0 && (
                    <p className="rounded-xl bg-[#2b2317] p-3 text-[#dec18a]">
                      Reason: {latest.rejection_codes.join(", ")}
                    </p>
                  )}
              </div>
            ) : (
              <Empty />
            )}
          </Card>
          <Card
            title="Technical acquisition"
            eyebrow={q ? String(q.qualification) : "NO CYCLE"}
          >
            {q ? (
              <>
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
                  {Object.entries(
                    (q.dimension_scores ?? {}) as Record<string, number>,
                  ).map(([k, v]) => (
                    <Metric
                      key={k}
                      label={k.replace("_score", "")}
                      value={v.toFixed(0)}
                    />
                  ))}
                </div>
                <p className="mt-4 text-sm text-[#819a94]">
                  Overall technical quality:{" "}
                  {Number(q.overall_score).toFixed(1)} / 100
                </p>
              </>
            ) : (
              <Empty />
            )}
          </Card>
        </div>
        <div className="mt-5 grid gap-5 xl:grid-cols-2">
          <Card title="Simulated bioimpedance" eyebrow="LEFT vs RIGHT · Ω">
            <Spectrum bis={d.bis} />
            <details className="mt-4">
              <summary className="cursor-pointer text-xs text-[#78c4b3]">
                Technical spectrum table
              </summary>
              {d.bis && (
                <table className="mt-3 w-full text-xs">
                  <thead>
                    <tr>
                      <th>Frequency</th>
                      <th>Left |Z|</th>
                      <th>Right |Z|</th>
                      <th>Left phase</th>
                      <th>Right phase</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.bis.left.map((x, i) => (
                      <tr key={x.frequency_hz}>
                        <td>{x.frequency_hz / 1000} kHz</td>
                        <td>{x.magnitude_ohm.toFixed(2)}</td>
                        <td>{d.bis!.right[i].magnitude_ohm.toFixed(2)}</td>
                        <td>{x.phase_deg.toFixed(2)}°</td>
                        <td>{d.bis!.right[i].phase_deg.toFixed(2)}°</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </details>
          </Card>
          <Card
            title="Personalized baseline"
            eyebrow={String(d.baseline.state)}
          >
            <div className="grid grid-cols-2 gap-3">
              <Metric
                label="observations"
                value={String(d.baseline.observation_count)}
              />
              <Metric
                label="span days"
                value={(
                  Number(d.baseline.simulated_span_seconds) / 86400
                ).toFixed(1)}
              />
              <Metric
                label="feature revision"
                value={String(d.baseline.feature_revision)}
              />
              <Metric
                label="baseline revision"
                value={String(d.baseline.baseline_revision)}
              />
            </div>
            {d.signal_processing && (
              <p className="mt-5 text-sm text-[#819a94]">
                Latest processed feature revision:{" "}
                {String(d.signal_processing.feature_revision)}
              </p>
            )}
          </Card>
        </div>
        <div className="mt-5 grid gap-5 xl:grid-cols-3">
          <Card title="Edge AI / TinyML" eyebrow="LOCAL · 0 CLOUD CALLS">
            <p className="text-sm">
              Aequor Tiny Autoencoder · {String(d.tinyml.model_revision)}
            </p>
            <p className="mt-1 text-xs text-[#819a94]">
              TFLite INT8 · 34-D personal baseline-relative vector ·{" "}
              {String(d.tinyml.model_size_bytes ?? "—")} bytes
            </p>
            <Flow
              items={[
                "Processed BIS",
                "Personal normalization",
                "34-D vector",
                "INT8 autoencoder",
                "Reconstruction",
                "Pattern novelty",
              ]}
            />
            {ml ? (
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Metric
                  label="MSE"
                  value={Number(ml.reconstruction_error_mse).toFixed(3)}
                />
                <Metric
                  label="novelty Z"
                  value={Number(ml.novelty_z).toFixed(3)}
                />
                <Metric
                  label="score"
                  value={Number(ml.model_novelty_score).toFixed(3)}
                />
                <Metric
                  label="latency ms"
                  value={Number(ml.inference_latency_ms).toFixed(3)}
                />
              </div>
            ) : (
              <Empty />
            )}
            <p className="mt-4 text-[10px] font-semibold tracking-wider text-[#d4b879]">
              PATTERN NOVELTY — NOT DISEASE PROBABILITY
            </p>
          </Card>
          <Card
            title="Temporal intelligence"
            eyebrow={String(t?.temporal_state ?? "NO HISTORY")}
          >
            <div className="grid grid-cols-2 gap-2">
              <Metric
                label="instant Z"
                value={String(t?.latest_novelty_z ?? "—")}
              />
              <Metric label="EWMA" value={String(t?.ewma_novelty ?? "—")} />
              <Metric label="CUSUM" value={String(t?.cusum_value ?? "—")} />
              <Metric
                label="persistence days"
                value={String(t?.persistence_duration_days ?? "—")}
              />
              <Metric
                label="slope / day"
                value={String(t?.recent_novelty_slope_per_day ?? "—")}
              />
            </div>
          </Card>
          <Card
            title="Confounder reasoning"
            eyebrow={String(c?.dominant_change_side ?? "UNDETERMINED")}
          >
            <div className="space-y-3">
              {[
                ["Bilateral coherence", c?.bilateral_coherence_score],
                ["Unilateral asymmetry", c?.unilateral_asymmetry_score],
                ["Systemic evidence", c?.systemic_bilateral_evidence],
                ["Temperature", c?.temperature_association_evidence],
                ["Residual motion", c?.residual_motion_evidence],
                ["Residual contact", c?.residual_contact_evidence],
                ["Transient", c?.transient_pattern_evidence],
              ].map(([k, v]) => (
                <Bar key={String(k)} label={String(k)} value={Number(v ?? 0)} />
              ))}
            </div>
          </Card>
        </div>
        <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_.9fr]">
          <Card
            title="Aequor Differential Index"
            eyebrow="PROTOTYPE RESEARCH INDEX · NOT DISEASE PROBABILITY"
          >
            <p className="text-6xl font-light">
              {dec?.adi == null ? "—" : Number(dec.adi).toFixed(1)}
              <span className="text-2xl text-[#819a94]"> / 100</span>
            </p>
            <p className="mt-2 text-xl">
              {String(dec?.surveillance_state ?? "CALIBRATING").replaceAll(
                "_",
                " ",
              )}
            </p>
            <div className="mt-5 grid grid-cols-2 gap-3">
              {Object.entries(components).map(([k, v]) => (
                <Bar key={k} label={k} value={v} />
              ))}
              {Object.entries(modifiers).map(([k, v]) => (
                <Bar key={k} label={`${k} modifier`} value={v} />
              ))}
            </div>
            <details className="mt-5">
              <summary className="cursor-pointer text-xs text-[#78c4b3]">
                ADI-v1 prototype engineering configuration
              </summary>
              <pre className="mt-3 overflow-auto rounded-xl bg-black/20 p-4 text-[11px] text-[#9db4ae]">
                {JSON.stringify(d.adi_configuration, null, 2)}
              </pre>
            </details>
          </Card>
          <Card title="System health" eyebrow="AUTHORITATIVE READINESS">
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(d.system_health).map(([k, v]) => (
                <Line key={k} k={k.replaceAll("_", " ")} v={v} />
              ))}
            </div>
          </Card>
        </div>
        <section className="mt-5 rounded-3xl border border-[#78c4b3]/20 bg-[#0c211e] p-7">
          <p className="text-xs font-semibold tracking-[.2em] text-[#78c4b3]">
            WHAT IS SIMULATED VS WHAT IS REAL SOFTWARE?
          </p>
          <div className="mt-5 grid gap-7 md:grid-cols-2">
            <List
              title="Simulated inputs"
              items={d.provenance.simulated_inputs}
            />
            <List
              title="Real executable algorithms"
              items={d.provenance.executable_software}
            />
          </div>
        </section>
      </div>
      <Style />
    </main>
  );
}
export function TopNav({ active }: { active: string }) {
  return (
    <nav className="border-b border-white/10 bg-[#081614]">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-4 px-5 py-4">
        <a href="/" className="font-semibold tracking-[.28em]">
          AEQUOR
        </a>
        <div className="flex gap-4 text-xs text-[#819a94]">
          {[
            ["Patient", "/patient"],
            ["Clinician", "/clinician"],
            ["Engineering", "/engineering"],
            ["Aequor Lab", "/lab"],
            ["Digital Twin", "/digital-twin"],
            ["Timeline", "/timeline"],
          ].map(([x, u]) => (
            <a
              key={x}
              href={u}
              className={active === x ? "text-[#78c4b3]" : "hover:text-white"}
            >
              {x}
            </a>
          ))}
        </div>
      </div>
    </nav>
  );
}
function Card({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-3xl border border-white/10 bg-[#0d201e] p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <h2 className="text-lg">{title}</h2>
        <span className="text-right text-[10px] font-semibold tracking-wider text-[#718e87]">
          {eyebrow}
        </span>
      </div>
      {children}
    </section>
  );
}
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/[.04] p-3">
      <p className="text-[10px] uppercase text-[#718e87]">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  );
}
function Line({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-white/[.05] py-2 text-xs">
      <span className="capitalize text-[#718e87]">{k}</span>
      <span>{v}</span>
    </div>
  );
}
function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="capitalize text-[#819a94]">
          {label.replaceAll("_", " ")}
        </span>
        <span>{value.toFixed(2)}</span>
      </div>
      <div className="mt-1 h-1 rounded bg-white/10">
        <div
          className="h-full rounded bg-[#62b8a7]"
          style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
        />
      </div>
    </div>
  );
}
function Empty() {
  return <p className="text-sm text-[#718e87]">No eligible cycle data.</p>;
}
function Flow({ items }: { items: string[] }) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 text-[10px] text-[#9eb5af]">
      {items.map((x, i) => (
        <span key={x}>
          {i > 0 && <b className="mr-2 text-[#54766e]">→</b>}
          {x}
        </span>
      ))}
    </div>
  );
}
function Spectrum({ bis }: { bis: E["bis"] }) {
  if (!bis) return <Empty />;
  const max = Math.max(
    ...bis.left.map((x) => x.magnitude_ohm),
    ...bis.right.map((x) => x.magnitude_ohm),
  );
  const line = (xs: Record<string, number>[]) =>
    xs
      .map((x, i) => `${5 + i * 18},${65 - (x.magnitude_ohm / max) * 50}`)
      .join(" ");
  return (
    <svg
      viewBox="0 0 100 70"
      className="h-52 w-full"
      role="img"
      aria-label="Simulated left and right bioimpedance magnitude spectrum"
    >
      <polyline
        points={line(bis.left)}
        fill="none"
        stroke="#63c4b0"
        strokeWidth="2"
      />
      <polyline
        points={line(bis.right)}
        fill="none"
        stroke="#d4b879"
        strokeWidth="2"
      />
    </svg>
  );
}
function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-sm text-white">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm text-[#8fa69f]">
        {items.map((x) => (
          <li key={x}>• {x}</li>
        ))}
      </ul>
    </div>
  );
}
function Style() {
  return (
    <style jsx global>{`
      .action {
        border-radius: 999px;
        background: #68c1ae;
        color: #09201b;
        padding: 0.7rem 1rem;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .action.secondary {
        background: transparent;
        color: #9db4ae;
        border: 1px solid rgba(255, 255, 255, 0.14);
      }
      table th,
      table td {
        padding: 0.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        text-align: left;
      }
    `}</style>
  );
}
