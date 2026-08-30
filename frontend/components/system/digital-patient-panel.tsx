"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchSimulation,
  performSimulationAction,
  stepSimulation,
  updateSimulationSpeed,
} from "@/lib/api/simulation";
import type {
  SimulationAction,
  SimulationClockEvent,
  SimulationConnectionState,
  SimulationLifecycle,
  SimulationSnapshot,
} from "@/lib/types/simulation";
import { connectSimulationSocket } from "@/lib/websocket/simulation-socket";


const SPEEDS = [1, 60, 3_600, 21_600, 86_400];
const STEPS = [
  { label: "+1 min", seconds: 60 },
  { label: "+1 hour", seconds: 3_600 },
  { label: "+6 hours", seconds: 21_600 },
  { label: "+1 day", seconds: 86_400 },
];

const lifecycleStyles: Record<SimulationLifecycle, string> = {
  UNINITIALIZED: "border-white/10 bg-white/[.04] text-[var(--muted)]",
  READY: "border-[rgba(107,184,230,.25)] bg-[rgba(107,184,230,.09)] text-[#8ed3f3]",
  RUNNING: "border-[rgba(93,228,207,.25)] bg-[rgba(93,228,207,.09)] text-[var(--aqua)]",
  PAUSED: "border-[rgba(233,185,110,.25)] bg-[rgba(233,185,110,.09)] text-[var(--amber)]",
};


function speedDescription(speed: number): string {
  if (speed === 1) return "1 real second = 1 simulated second";
  if (speed === 60) return "1 real second = 1 simulated minute";
  if (speed === 3_600) return "1 real second = 1 simulated hour";
  if (speed === 21_600) return "1 real second = 6 simulated hours";
  if (speed === 86_400) return "1 real second = 1 simulated day";
  return `1 real second = ${speed.toLocaleString()} simulated seconds`;
}


function ClockDisplay({ timestamp }: { timestamp: string }) {
  const value = new Date(timestamp);
  const date = new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(value);
  const time = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    timeZone: "UTC",
  }).format(value);

  return (
    <div>
      <p className="text-lg font-light tracking-[-0.02em] text-[#aac4c0] sm:text-xl">{date}</p>
      <p className="mt-1 text-4xl font-light tabular-nums tracking-[-0.04em] text-white sm:text-5xl">{time}</p>
      <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Simulated timeline · UTC</p>
    </div>
  );
}


export function DigitalPatientPanel() {
  const [snapshot, setSnapshot] = useState<SimulationSnapshot | null>(null);
  const [connection, setConnection] = useState<SimulationConnectionState>("CONNECTING");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSnapshot = useCallback(async (signal?: AbortSignal) => {
    try {
      const next = await fetchSimulation(signal);
      setSnapshot(next);
      setError(null);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      setError("Digital Patient service is unavailable. Reconnection is automatic.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const request = window.setTimeout(() => void loadSnapshot(controller.signal), 0);
    return () => {
      controller.abort();
      window.clearTimeout(request);
    };
  }, [loadSnapshot]);

  useEffect(() => connectSimulationSocket({
    onStateChange: (state) => {
      setConnection(state);
      if (state === "CONNECTED") void loadSnapshot();
    },
    onClock: (event: SimulationClockEvent) => {
      setSnapshot((current) => current ? {
        ...current,
        lifecycle: event.lifecycle,
        wall_clock_time: event.wall_clock_time,
        simulated_time: event.simulated_time,
        speed_multiplier: event.speed_multiplier,
      } : current);
    },
  }), [loadSnapshot]);

  const execute = async (operation: () => Promise<SimulationSnapshot>) => {
    setBusy(true);
    setError(null);
    try {
      setSnapshot(await operation());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Simulation action failed.");
    } finally {
      setBusy(false);
    }
  };

  const action = (name: SimulationAction) => void execute(() => performSimulationAction(name));
  const lifecycle = snapshot?.lifecycle ?? "UNINITIALIZED";
  const connected = connection === "CONNECTED";
  const canStep = connected && !busy && (lifecycle === "READY" || lifecycle === "PAUSED");

  return (
    <section className="mt-12 overflow-hidden rounded-3xl border border-[rgba(93,228,207,.16)] bg-[rgba(7,24,28,.82)] shadow-[0_28px_100px_rgba(0,0,0,.22)] backdrop-blur-xl sm:mt-16">
      <div className="flex flex-col gap-4 border-b border-[var(--line)] px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--aqua)]">Digital patient</p>
          <h2 className="mt-2 text-xl font-medium tracking-[-0.02em] text-white">{snapshot?.patient.display_name ?? "Synthetic session"}</h2>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {snapshot ? `Synthetic Patient · ID ${snapshot.patient.patient_id}` : "Awaiting backend-authoritative identity"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold tracking-[0.14em] ${lifecycleStyles[lifecycle]}`}>{lifecycle}</span>
          <span className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold tracking-[0.14em] ${connected ? "border-[rgba(93,228,207,.2)] text-[var(--aqua)]" : "border-[rgba(255,143,136,.22)] text-[var(--red)]"}`}>{connection}</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1.05fr_.95fr]">
        <div className="border-b border-[var(--line)] p-5 sm:p-7 lg:border-r lg:border-b-0">
          <p className="mb-5 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Simulated time</p>
          {snapshot && connected ? (
            <ClockDisplay timestamp={snapshot.simulated_time} />
          ) : (
            <div className="min-h-28 rounded-xl border border-dashed border-white/10 p-5 text-sm leading-6 text-[var(--muted)]">
              Authoritative simulation time is unavailable. No local clock is running as a substitute.
            </div>
          )}

          <div className="mt-8 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[var(--line)] bg-white/[.018] p-4">
              <p className="text-[9px] uppercase tracking-[0.18em] text-[var(--muted)]">Seed</p>
              <p className="mt-2 font-mono text-sm text-[#d9ece8]">{snapshot?.seed ?? "—"}</p>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-white/[.018] p-4">
              <p className="text-[9px] uppercase tracking-[0.18em] text-[var(--muted)]">Provenance</p>
              <p className="mt-2 text-sm font-medium text-[#8ed3f3]">{snapshot?.data_provenance ?? "—"}</p>
            </div>
          </div>
        </div>

        <div className="p-5 sm:p-7">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Simulation speed</p>
          <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-3 xl:grid-cols-5">
            {SPEEDS.map((speed) => (
              <button
                key={speed}
                type="button"
                disabled={!connected || busy}
                onClick={() => void execute(() => updateSimulationSpeed(speed))}
                className={`rounded-lg border px-2 py-2.5 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-35 ${snapshot?.speed_multiplier === speed ? "border-[rgba(93,228,207,.4)] bg-[var(--aqua-soft)] text-[var(--aqua)]" : "border-[var(--line)] bg-white/[.02] text-[#9eb3b0] hover:border-[rgba(93,228,207,.25)]"}`}
              >
                {speed.toLocaleString()}×
              </button>
            ))}
          </div>
          <p className="mt-3 min-h-5 text-xs text-[#8fa7a3]">{snapshot ? speedDescription(snapshot.speed_multiplier) : "Speed is backend controlled."}</p>

          <div className="mt-7 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4">
            {lifecycle === "UNINITIALIZED" && <ControlButton label="Initialize" enabled={connected && !busy} onClick={() => action("create")} />}
            <ControlButton label="Start" enabled={connected && !busy && lifecycle === "READY"} onClick={() => action("start")} />
            <ControlButton label="Pause" enabled={connected && !busy && lifecycle === "RUNNING"} onClick={() => action("pause")} />
            <ControlButton label="Resume" enabled={connected && !busy && lifecycle === "PAUSED"} onClick={() => action("resume")} />
            <ControlButton label="Reset" enabled={connected && !busy && lifecycle !== "UNINITIALIZED"} onClick={() => action("reset")} />
          </div>

          <div className="mt-7 border-t border-[var(--line)] pt-5">
            <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Deterministic manual step</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {STEPS.map((step) => (
                <button key={step.seconds} type="button" disabled={!canStep} onClick={() => void execute(() => stepSimulation(step.seconds))} className="rounded-full border border-[var(--line)] px-3 py-1.5 text-[10px] font-medium text-[#9eb3b0] transition-colors hover:border-[rgba(93,228,207,.25)] hover:text-[var(--aqua)] disabled:cursor-not-allowed disabled:opacity-30">{step.label}</button>
              ))}
            </div>
          </div>

          {error && <p role="alert" className="mt-5 rounded-xl border border-[rgba(255,143,136,.18)] bg-[rgba(255,143,136,.06)] px-4 py-3 text-xs leading-5 text-[var(--red)]">{error}</p>}
        </div>
      </div>
    </section>
  );
}


function ControlButton({ label, enabled, onClick }: { label: string; enabled: boolean; onClick: () => void }) {
  return (
    <button type="button" disabled={!enabled} onClick={onClick} className="rounded-lg border border-[rgba(93,228,207,.2)] bg-[rgba(93,228,207,.06)] px-3 py-2.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--aqua)] transition-colors hover:bg-[rgba(93,228,207,.12)] disabled:cursor-not-allowed disabled:border-white/[.06] disabled:bg-white/[.02] disabled:text-[#526361]">
      {label}
    </button>
  );
}

