import type { BilateralBioimpedanceSweep } from "@/lib/types/bioimpedance";


export function MeasurementTable({ sweep }: { sweep: BilateralBioimpedanceSweep }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-[var(--line)] text-[9px] uppercase tracking-[0.13em] text-[var(--muted)]">
            <th className="px-3 py-3 font-medium">Frequency</th>
            <th className="px-3 py-3 font-medium">Left R</th>
            <th className="px-3 py-3 font-medium">Left X</th>
            <th className="px-3 py-3 font-medium">Left |Z|</th>
            <th className="px-3 py-3 font-medium">Left phase</th>
            <th className="px-3 py-3 font-medium">Right R</th>
            <th className="px-3 py-3 font-medium">Right X</th>
            <th className="px-3 py-3 font-medium">Right |Z|</th>
            <th className="px-3 py-3 font-medium">Right phase</th>
          </tr>
        </thead>
        <tbody>
          {sweep.left.points.map((left, index) => {
            const right = sweep.right.points[index];
            return (
              <tr key={left.frequency_hz} className="border-b border-white/[.045] font-mono tabular-nums text-[#b9cdca] last:border-0">
                <td className="px-3 py-3 text-white">{(left.frequency_hz / 1000).toFixed(0)} kHz</td>
                <td className="px-3 py-3">{left.resistance_ohm.toFixed(2)} Ω</td>
                <td className="px-3 py-3">{left.reactance_ohm.toFixed(2)} Ω</td>
                <td className="px-3 py-3">{left.magnitude_ohm.toFixed(2)} Ω</td>
                <td className="px-3 py-3">{left.phase_deg.toFixed(2)}°</td>
                <td className="px-3 py-3">{right.resistance_ohm.toFixed(2)} Ω</td>
                <td className="px-3 py-3">{right.reactance_ohm.toFixed(2)} Ω</td>
                <td className="px-3 py-3">{right.magnitude_ohm.toFixed(2)} Ω</td>
                <td className="px-3 py-3">{right.phase_deg.toFixed(2)}°</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

