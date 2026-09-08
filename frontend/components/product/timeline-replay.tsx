"use client";

import { useCallback, useEffect, useState } from "react";
import { TopNav } from "./engineering-console";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type Event = {
  event_id: string; sequence_index: number; simulated_time: string; event_type: string; source: string; title: string; summary: string;
  scenario_ground_truth: Record<string, unknown> | null; measurement_summary: Record<string, unknown> | null;
  ml_summary: Record<string, unknown> | null; temporal_summary: Record<string, unknown> | null;
  confounder_summary: Record<string, unknown> | null; decision_summary: Record<string, unknown> | null;
};
type Replay = {
  title: string; observer_only: boolean; ground_truth_disclosure: string; duration_seconds: number; measurement_count: number; qualified_measurements: number; rejected_measurements: number;
  session: { session_id: string; event_count: number; baseline_status: string; starting_state: string; current_state: string; reset_boundary: string };
  events: Event[];
  trend_series: { bilateral: { left: number | null; right: number | null }[]; novelty: { novelty_z: number | null; ewma: number | null }[]; adi: { adi: number | null }[] };
  state_bands: { state: string; start_time: string; end_time: string }[];
};

export function TimelineReplay() {
  const [truth, setTruth] = useState(true);
  const [data, setData] = useState<Replay | null>(null);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState(0);
  const load = useCallback(async (showTruth: boolean) => {
    try { const response=await fetch(`${api}/api/v1/views/timeline?include_ground_truth=${showTruth}`); if(!response.ok)throw new Error(); const next:Replay=await response.json(); setData(next);setError(false);setSelected((index) => Math.min(index, Math.max(0, next.events.length - 1))); } catch { setError(true) }
  }, []);
  useEffect(() => {
    const first = setTimeout(() => void load(truth), 0);
    const interval = setInterval(() => void load(truth), 4000);
    return () => { clearTimeout(first); clearInterval(interval); };
  }, [load, truth]);
  if (error) return <main className="min-h-screen bg-[#081310] p-8 text-white"><b className="text-[#caaa68]">BACKEND UNAVAILABLE</b><p className="mt-3 text-sm">Recorded evidence is hidden until a fresh response is available.</p></main>;
  if (!data) return <main className="min-h-screen bg-[#081310] p-8 text-white">Preparing longitudinal replay…</main>;
  const event = data.events[selected] ?? null;
  return <main className="min-h-screen bg-[#081310] text-[#e7efeb]">
    <TopNav active="Timeline" />
    <div className="mx-auto max-w-[1500px] px-5 py-7 sm:px-8">
      <header className="rounded-[2rem] border border-[#caaa68]/20 bg-[#121f1a] p-6 sm:p-9">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div><p className="text-[11px] font-bold tracking-[.22em] text-[#caaa68]">RECORDED EVIDENCE · NO ALGORITHM RECOMPUTATION</p><h1 className="mt-3 text-4xl font-light sm:text-6xl">{data.title}</h1><p className="mt-4 max-w-3xl text-sm leading-6 text-[#99aaa4]">Replay shows the evidence and decisions stored when each cycle occurred. Historical novelty, ADI, and state are never recalculated.</p></div>
          <label className="flex cursor-pointer items-center gap-3 rounded-full border border-white/10 bg-white/[.04] px-4 py-3 text-xs"><input type="checkbox" checked={truth} onChange={(e) => { setTruth(e.target.checked); setSelected(0); }} className="accent-[#caaa68]" />SHOW DIGITAL-TWIN GROUND TRUTH</label>
        </div>
        {truth && <p className="mt-5 rounded-xl border border-[#caaa68]/20 bg-[#caaa68]/[.07] p-3 text-xs text-[#d7c08c]">{data.ground_truth_disclosure}</p>}
      </header>
      <section className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-6">
        <Metric label="Session duration" value={`${(data.duration_seconds / 86400).toFixed(1)} days`} /><Metric label="Measurements" value={String(data.measurement_count)} /><Metric label="Qualified" value={String(data.qualified_measurements)} /><Metric label="Rejected" value={String(data.rejected_measurements)} /><Metric label="Starting state" value={pretty(data.session.starting_state)} /><Metric label="Current state" value={pretty(data.session.current_state)} />
      </section>
      <section className="mt-5 rounded-3xl border border-white/10 bg-[#0d1d19] p-5 sm:p-7">
        <div className="flex items-center justify-between"><div><p className="text-[10px] font-bold tracking-[.2em] text-[#78978f]">MASTER TIMELINE</p><h2 className="mt-2 text-2xl">The experiment, event by event</h2></div><span className="text-xs text-[#718982]">{data.session.event_count} events</span></div>
        {data.events.length ? <><div className="mt-7 overflow-x-auto pb-3"><div className="flex min-w-max items-center">{data.events.map((item, index) => <button key={item.event_id} onClick={() => setSelected(index)} className="group flex w-28 flex-col items-center text-center"><span className={`h-3 w-3 rounded-full ring-4 ${index === selected ? "bg-[#f0c778] ring-[#f0c778]/20" : "bg-[#659f91] ring-[#659f91]/10"}`} /><span className="my-2 h-px w-full bg-white/10" /><span className="line-clamp-2 h-8 text-[9px] uppercase text-[#849b95] group-hover:text-white">{item.title}</span></button>)}</div></div><label className="mt-4 block text-[10px] uppercase tracking-wider text-[#718982]">Replay scrubber<input aria-label="Replay scrubber" className="mt-3 w-full accent-[#caaa68]" type="range" min={0} max={Math.max(0, data.events.length - 1)} value={selected} onChange={(e) => setSelected(Number(e.target.value))} /></label></> : <Empty text="Run an experiment in Aequor Lab to populate replay history." />}
      </section>
      <section className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <div className="space-y-5">
          <Trend title="Bilateral relative pattern" legend="LEFT / RIGHT personalized observation"><Chart series={[data.trend_series.bilateral.map((x) => x.left), data.trend_series.bilateral.map((x) => x.right)]} colors={["#6fd1bb", "#d0ae6a"]} /></Trend>
          <Trend title="Novelty and temporal accumulation" legend="Novelty z / EWMA"><Chart series={[data.trend_series.novelty.map((x) => x.novelty_z), data.trend_series.novelty.map((x) => x.ewma)]} colors={["#8bc5ee", "#b994df"]} /></Trend>
          <Trend title="Aequor Deviation Index" legend="Recorded ADI — prototype research index"><Chart series={[data.trend_series.adi.map((x) => x.adi)]} colors={["#e1a96c"]} /></Trend>
          <section className="rounded-3xl border border-white/10 bg-[#0d1d19] p-6"><p className="text-[10px] font-bold tracking-[.18em] text-[#78978f]">RECORDED STATE BANDS</p><div className="mt-4 flex min-h-14 overflow-hidden rounded-xl border border-white/10">{data.state_bands.length ? data.state_bands.map((band, index) => <div key={`${band.state}-${index}`} className={`flex min-w-24 flex-1 items-center justify-center p-2 text-center text-[9px] font-bold ${stateColor(band.state)}`}>{pretty(band.state)}</div>) : <p className="m-auto text-xs text-[#718982]">No recorded decision transition yet.</p>}</div></section>
        </div>
        <aside className="rounded-3xl border border-[#6fb9a8]/20 bg-[#10231f] p-6 xl:sticky xl:top-5 xl:self-start">
          <p className="text-[10px] font-bold tracking-[.2em] text-[#70bba9]">AT THIS MOMENT</p>
          {event ? <><div className="mt-3 flex items-start justify-between gap-4"><h2 className="text-2xl">{event.title}</h2><span className="rounded-full bg-white/[.05] px-3 py-1 text-[9px] text-[#8ea29d]">{event.source}</span></div><p className="mt-2 text-xs text-[#789089]">{new Date(event.simulated_time).toLocaleString()} · #{event.sequence_index}</p><p className="mt-4 text-sm leading-6 text-[#a4b4af]">{event.summary}</p>{event.event_type === "MEASUREMENT_REJECTED" && <div className="mt-4 rounded-xl border border-[#d18a78]/20 bg-[#d18a78]/[.07] p-4 text-sm text-[#daa091]">{String(event.measurement_summary?.rejection_reasons ?? "Technical quality rejection")}<br /><b>Measurement not used · Decision state unchanged</b></div>}{truth && event.scenario_ground_truth && <Detail title="WHAT THE DIGITAL TWIN WAS DOING" rows={[["Scenario", event.scenario_ground_truth.scenario_type], ["Configured arm", event.scenario_ground_truth.affected_arm], ["Progression", `${(Number(event.scenario_ground_truth.severity ?? 0) * 100).toFixed(1)}%`]]} />}<Detail title="WHAT AEQUOR OBSERVED" rows={observed(event)} /><Detail title="WHAT AEQUOR DECIDED" rows={decided(event)} /></> : <Empty text="Select an event to inspect its recorded evidence." />}
        </aside>
      </section>
      <p className="mt-5 text-center text-xs text-[#647b75]">Rejected markers never create fake ML or ADI points.</p>
    </div>
  </main>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-2xl border border-white/10 bg-[#0d1d19] p-4"><p className="text-[9px] uppercase tracking-wider text-[#718982]">{label}</p><p className="mt-2 text-sm">{value}</p></div>; }
function Trend({ title, legend, children }: { title: string; legend: string; children: React.ReactNode }) { return <section className="rounded-3xl border border-white/10 bg-[#0d1d19] p-6"><div className="flex flex-col justify-between gap-1 sm:flex-row"><h2 className="text-xl">{title}</h2><p className="text-[10px] text-[#718982]">{legend}</p></div>{children}</section>; }
function Chart({ series, colors }: { series: (number | null)[][]; colors: string[] }) { const vals = series.flatMap((x) => x).filter((x): x is number => x != null); if (!vals.length) return <Empty text="No eligible recorded points." />; const min = Math.min(...vals), max = Math.max(...vals); const points = (xs: (number | null)[]) => xs.map((v, i) => v == null ? null : `${5 + i * (90 / Math.max(1, xs.length - 1))},${58 - ((v - min) / (max - min || 1)) * 45}`).filter(Boolean).join(" "); return <svg viewBox="0 0 100 65" className="mt-4 h-40 w-full" role="img" aria-label="Recorded longitudinal series">{series.map((x, i) => <polyline key={i} points={points(x)} fill="none" stroke={colors[i]} strokeWidth="2" />)}<line x1="5" y1="59" x2="96" y2="59" stroke="#49615b" strokeWidth=".3" /></svg>; }
function Detail({ title, rows }: { title: string; rows: [string, unknown][] }) { const shown = rows.filter(([, value]) => value != null); return <section className="mt-5 border-t border-white/10 pt-5"><h3 className="text-[10px] font-bold tracking-[.16em] text-[#78978f]">{title}</h3>{shown.length ? <div className="mt-3 space-y-2">{shown.map(([key, value]) => <div key={key} className="flex justify-between gap-4 text-xs"><span className="text-[#718982]">{key}</span><span className="text-right">{typeof value === "number" ? value.toFixed(2) : String(value)}</span></div>)}</div> : <p className="mt-3 text-xs text-[#647b75]">No update was recorded for this event.</p>}</section>; }
function observed(e: Event): [string, unknown][] { return [["Technical quality", e.measurement_summary?.technical_quality], ["LEFT relative pattern", e.measurement_summary?.left_relative_pattern], ["RIGHT relative pattern", e.measurement_summary?.right_relative_pattern], ["ML novelty z", e.ml_summary?.novelty_z], ["EWMA", e.temporal_summary?.ewma_novelty], ["CUSUM", e.temporal_summary?.cusum_value], ["Persistence days", e.temporal_summary?.persistence_duration_days], ["Unilateral evidence", e.confounder_summary?.unilateral_asymmetry_score], ["Systemic evidence", e.confounder_summary?.systemic_bilateral_evidence]]; }
function decided(e: Event): [string, unknown][] { return [["ADI", e.decision_summary?.adi], ["Surveillance state", e.decision_summary?.surveillance_state], ["Observed side", e.decision_summary?.dominant_observed_side], ["Explanation", Array.isArray(e.decision_summary?.explanations) ? e.decision_summary.explanations.join(" ") : null]]; }
function stateColor(state: string) { if (state === "CLINICAL_REVIEW_RECOMMENDED") return "bg-[#c9786b]/35 text-[#f0b2a8]"; if (state === "PERSISTENT_DEVIATION") return "bg-[#d3a35e]/30 text-[#e8c58d]"; if (state === "OBSERVING_CHANGE") return "bg-[#7a8ec5]/30 text-[#aebbe1]"; return "bg-[#5ca793]/25 text-[#9fd8c8]"; }
function Empty({ text }: { text: string }) { return <p className="mt-5 rounded-xl bg-white/[.03] p-5 text-sm text-[#718982]">{text}</p>; }
function pretty(value: string) { return value.replaceAll("_", " "); }
