import type { ConnectionState, DataProvenance, SubsystemStatus } from "@/lib/types/system";


type StatusValue = SubsystemStatus | ConnectionState | DataProvenance;

const styles: Record<StatusValue, string> = {
  READY: "border-[rgba(93,228,207,.22)] bg-[rgba(93,228,207,.09)] text-[var(--aqua)]",
  CONNECTED: "border-[rgba(93,228,207,.22)] bg-[rgba(93,228,207,.09)] text-[var(--aqua)]",
  SIMULATED: "border-[rgba(107,184,230,.22)] bg-[rgba(107,184,230,.09)] text-[#8ed3f3]",
  HARDWARE: "border-[rgba(93,228,207,.22)] bg-[rgba(93,228,207,.09)] text-[var(--aqua)]",
  CONNECTING: "border-[rgba(233,185,110,.22)] bg-[rgba(233,185,110,.09)] text-[var(--amber)]",
  NOT_IMPLEMENTED: "border-white/10 bg-white/[.035] text-[#839693]",
  DISCONNECTED: "border-[rgba(255,143,136,.22)] bg-[rgba(255,143,136,.08)] text-[var(--red)]",
  ERROR: "border-[rgba(255,143,136,.22)] bg-[rgba(255,143,136,.08)] text-[var(--red)]",
};


export function StatusPill({ value, live = false }: { value: StatusValue; live?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-[0.12em] ${styles[value]}`}>
      <span className={`relative h-1.5 w-1.5 rounded-full bg-current ${live ? "live-ring" : ""}`} />
      {value.replaceAll("_", " ")}
    </span>
  );
}

