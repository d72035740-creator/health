import type { BioimpedanceTwinConfiguration, ColeModelParameters } from "@/lib/types/bioimpedance";


function ParameterSet({ label, parameters }: { label: string; parameters: ColeModelParameters }) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-white/[.018] p-4">
      <p className="text-[9px] font-semibold uppercase tracking-[0.17em] text-[var(--muted)]">{label}</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        <dt className="text-[var(--muted)]">R0</dt><dd className="text-right font-mono text-[#d7eae7]">{parameters.r_zero_ohm.toFixed(1)} Ω</dd>
        <dt className="text-[var(--muted)]">R∞</dt><dd className="text-right font-mono text-[#d7eae7]">{parameters.r_infinity_ohm.toFixed(1)} Ω</dd>
        <dt className="text-[var(--muted)]">tau</dt><dd className="text-right font-mono text-[#d7eae7]">{(parameters.tau_seconds * 1_000_000).toFixed(1)} µs</dd>
        <dt className="text-[var(--muted)]">beta</dt><dd className="text-right font-mono text-[#d7eae7]">{parameters.beta.toFixed(2)}</dd>
      </dl>
    </div>
  );
}


export function ModelInspector({ config }: { config: BioimpedanceTwinConfiguration }) {
  return (
    <aside className="rounded-2xl border border-[var(--line)] bg-white/[.018] p-5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--aqua)]">Model inspector</p>
      <p className="mt-3 text-lg font-medium text-white">{config.model_name}</p>
      <p className="mt-1 font-mono text-xs text-[#8ed3f3]">Revision {config.model_revision}</p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
        <ParameterSet label="Left arm" parameters={config.left_parameters} />
        <ParameterSet label="Right arm" parameters={config.right_parameters} />
      </div>
      <p className="mt-4 text-xs leading-5 text-[var(--muted)]">Synthetic model parameters — not clinical reference values.</p>
    </aside>
  );
}

