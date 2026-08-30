"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusCard } from "@/components/system/status-card";
import { BioimpedanceTwinPanel } from "@/components/bioimpedance/bioimpedance-twin-panel";
import { DigitalPatientPanel } from "@/components/system/digital-patient-panel";
import { VirtualSensorLab } from "@/components/sensors/virtual-sensor-lab";
import { fetchSystemStatus } from "@/lib/api/system";
import type { ConnectionState, SystemHeartbeat, SystemStatus } from "@/lib/types/system";
import { connectSystemSocket } from "@/lib/websocket/system-socket";


export function SystemDashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [streamState, setStreamState] = useState<ConnectionState>("CONNECTING");
  const [lastHeartbeat, setLastHeartbeat] = useState<string | null>(null);

  const loadStatus = useCallback(async (signal?: AbortSignal) => {
    try {
      const nextStatus = await fetchSystemStatus(signal);
      setStatus(nextStatus);
      setBackendConnected(true);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setBackendConnected(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const initialRequest = window.setTimeout(() => void loadStatus(controller.signal), 0);
    const timer = window.setInterval(() => void loadStatus(), 5000);
    return () => {
      controller.abort();
      window.clearTimeout(initialRequest);
      window.clearInterval(timer);
    };
  }, [loadStatus]);

  useEffect(() => connectSystemSocket({
    onStateChange: setStreamState,
    onHeartbeat: (heartbeat: SystemHeartbeat) => {
      setLastHeartbeat(heartbeat.timestamp);
      setBackendConnected(heartbeat.backend_status === "READY");
    },
  }), []);

  const unavailable = "DISCONNECTED" as const;
  const futureStatus = (value: SystemStatus[keyof SystemStatus] | undefined) =>
    backendConnected && value ? value as "NOT_IMPLEMENTED" | "READY" | "ERROR" : unavailable;

  const cards = [
    { label: "Frontend", status: "READY" as const, detail: "Responsive product interface is operational." },
    { label: "Backend", status: backendConnected ? status?.backend ?? "READY" : unavailable, detail: backendConnected ? "REST service is responding." : "REST service is unavailable; retrying automatically." },
    { label: "Live Stream", status: streamState, live: streamState === "CONNECTED", detail: lastHeartbeat ? `System heartbeat received ${new Date(lastHeartbeat).toLocaleTimeString()}.` : "Establishing the heartbeat channel." },
    { label: "Sensor Source", status: backendConnected ? status?.data_provenance ?? unavailable : unavailable, detail: backendConnected ? "Provenance is explicit; no physical sensors are connected." : "Source provenance is unavailable while the backend is offline." },
    { label: "Digital Patient", status: futureStatus(status?.digital_patient_engine), detail: "Authoritative synthetic identity and simulation clock." },
    { label: "Bioimpedance Twin", status: futureStatus(status?.bioimpedance_digital_twin), detail: "Synchronized synthetic Cole-model acquisition is ready." },
    { label: "Virtual Sensors", status: futureStatus(status?.virtual_imu), detail: "Bilateral raw IMU, skin temperature, and contact sensing are ready." },
    { label: "Quality Engine", status: futureStatus(status?.quality_engine), detail: "Measurement-quality algorithms are reserved for Phase 4." },
    { label: "Edge AI", status: futureStatus(status?.ml_engine), detail: "No model, inference score, or clinical decision exists." },
  ];

  return (
    <section className="flex-1 py-14 sm:py-20 lg:py-24">
      <div className="max-w-4xl">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[rgba(233,185,110,.22)] bg-[rgba(233,185,110,.07)] px-3 py-1.5 text-[10px] font-semibold tracking-[0.18em] text-[var(--amber)]">
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          SIMULATION PROTOTYPE
        </div>
        <h1 className="text-balance text-4xl font-light leading-[1.08] tracking-[-0.04em] text-white sm:text-6xl lg:text-7xl">
          Personalized Edge-AI<br />
          <span className="text-[#9db9b5]">Lymphedema Surveillance</span>
        </h1>
        <p className="mt-6 max-w-2xl text-sm leading-7 text-[var(--muted)] sm:text-base">
          A foundational architecture for bilateral wearable surveillance—designed around explicit provenance, replaceable sensing boundaries, and conservative system states.
        </p>
      </div>

      <DigitalPatientPanel />
      <BioimpedanceTwinPanel backendConnected={backendConnected} />
      <VirtualSensorLab backendConnected={backendConnected} />

      <div className="mt-12 flex items-center justify-between border-b border-[var(--line)] pb-4 sm:mt-16">
        <h2 className="text-xs font-semibold uppercase tracking-[0.22em] text-[#b7cbc8]">System readiness</h2>
        <span className="text-[10px] uppercase tracking-[0.16em] text-[var(--muted)]">Authoritative live status</span>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => <StatusCard key={card.label} {...card} />)}
      </div>

      <aside className="mt-5 flex gap-4 rounded-2xl border border-[rgba(107,184,230,.15)] bg-[rgba(14,31,37,.68)] p-5 text-sm leading-6 text-[#a9bfbc]">
        <span aria-hidden="true" className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[#69aeca] text-[10px] text-[#8ed3f3]">i</span>
        <p><strong className="font-medium text-[#d1e4e1]">Prototype transparency.</strong> Sensor acquisition is simulated in this prototype. Physiological sensing and clinical validation are future hardware-validation stages.</p>
      </aside>
    </section>
  );
}
