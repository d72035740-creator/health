import type { ConnectionState, DataProvenance, SubsystemStatus } from "@/lib/types/system";
import { StatusPill } from "@/components/ui/status-pill";


type StatusValue = SubsystemStatus | ConnectionState | DataProvenance;


export function StatusCard({
  label,
  detail,
  status,
  live = false,
}: {
  label: string;
  detail: string;
  status: StatusValue;
  live?: boolean;
}) {
  return (
    <article className="group relative min-h-40 overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-5 backdrop-blur-xl transition-colors hover:border-[rgba(93,228,207,.24)]">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[rgba(93,228,207,.24)] to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{label}</p>
        <StatusPill value={status} live={live} />
      </div>
      <p className="mt-9 max-w-[28ch] text-sm leading-6 text-[#b8cbc8]">{detail}</p>
    </article>
  );
}

