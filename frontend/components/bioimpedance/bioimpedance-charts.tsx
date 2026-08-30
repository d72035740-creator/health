"use client";

import { useEffect, useRef, useState } from "react";

import type { BioimpedanceFrequencyPoint } from "@/lib/types/bioimpedance";


interface ChartProps {
  left: BioimpedanceFrequencyPoint[];
  right: BioimpedanceFrequencyPoint[];
}

interface PlotGeometry {
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
}


function useChartWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(300, entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return { ref, width };
}


function path(points: BioimpedanceFrequencyPoint[], x: (point: BioimpedanceFrequencyPoint) => number, y: (point: BioimpedanceFrequencyPoint) => number) {
  return points.map((point, index) => `${index === 0 ? "M" : "L"}${x(point).toFixed(2)},${y(point).toFixed(2)}`).join(" ");
}


function Legend() {
  return (
    <div className="mb-3 flex items-center gap-5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#9fb5b2]">
      <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[var(--aqua)]" />Left arm</span>
      <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[#8ed3f3]" />Right arm</span>
    </div>
  );
}


export function ImpedanceSpectrumChart({ left, right }: ChartProps) {
  const { ref, width } = useChartWidth();
  const geometry: PlotGeometry = { width, height: 290, left: 58, right: 18, top: 16, bottom: 48 };
  const plotWidth = geometry.width - geometry.left - geometry.right;
  const plotHeight = geometry.height - geometry.top - geometry.bottom;
  const all = [...left, ...right];
  const logMin = Math.log10(Math.min(...all.map((point) => point.frequency_hz)));
  const logMax = Math.log10(Math.max(...all.map((point) => point.frequency_hz)));
  const magnitudes = all.map((point) => point.magnitude_ohm);
  const rawMin = Math.min(...magnitudes);
  const rawMax = Math.max(...magnitudes);
  const padding = Math.max(5, (rawMax - rawMin) * 0.1);
  const yMin = rawMin - padding;
  const yMax = rawMax + padding;
  const x = (point: BioimpedanceFrequencyPoint) => geometry.left + ((Math.log10(point.frequency_hz) - logMin) / (logMax - logMin)) * plotWidth;
  const y = (point: BioimpedanceFrequencyPoint) => geometry.top + ((yMax - point.magnitude_ohm) / (yMax - yMin)) * plotHeight;
  const yTicks = Array.from({ length: 5 }, (_, index) => yMin + ((yMax - yMin) * index) / 4);

  return (
    <div ref={ref}>
      <Legend />
      <svg width="100%" height={geometry.height} viewBox={`0 0 ${width} ${geometry.height}`} role="img" aria-labelledby="spectrum-title spectrum-desc">
        <title id="spectrum-title">Bilateral impedance magnitude spectrum</title>
        <desc id="spectrum-desc">Log-frequency comparison of simulated left and right arm impedance magnitude in ohms.</desc>
        {yTicks.map((tick) => {
          const tickY = geometry.top + ((yMax - tick) / (yMax - yMin)) * plotHeight;
          return <g key={tick}><line x1={geometry.left} x2={width - geometry.right} y1={tickY} y2={tickY} stroke="rgba(140,167,164,.13)" /><text x={geometry.left - 9} y={tickY + 4} textAnchor="end" fill="#8ca7a4" fontSize="11">{tick.toFixed(0)}</text></g>;
        })}
        {left.map((point) => <text key={point.frequency_hz} x={x(point)} y={geometry.height - 25} textAnchor="middle" fill="#8ca7a4" fontSize="11">{point.frequency_hz / 1000}k</text>)}
        <line x1={geometry.left} x2={width - geometry.right} y1={geometry.top + plotHeight} y2={geometry.top + plotHeight} stroke="rgba(170,196,192,.35)" />
        <line x1={geometry.left} x2={geometry.left} y1={geometry.top} y2={geometry.top + plotHeight} stroke="rgba(170,196,192,.35)" />
        <path d={path(left, x, y)} fill="none" stroke="var(--aqua)" strokeWidth="2" />
        <path d={path(right, x, y)} fill="none" stroke="#8ed3f3" strokeWidth="2" />
        {left.map((point) => <circle key={`l-${point.frequency_hz}`} cx={x(point)} cy={y(point)} r="3.5" fill="var(--aqua)"><title>{`Left ${point.frequency_hz / 1000} kHz: ${point.magnitude_ohm.toFixed(2)} Ω`}</title></circle>)}
        {right.map((point) => <circle key={`r-${point.frequency_hz}`} cx={x(point)} cy={y(point)} r="3.5" fill="#8ed3f3"><title>{`Right ${point.frequency_hz / 1000} kHz: ${point.magnitude_ohm.toFixed(2)} Ω`}</title></circle>)}
        <text x={geometry.left + plotWidth / 2} y={geometry.height - 4} textAnchor="middle" fill="#a9bfbc" fontSize="12">Frequency (kHz, logarithmic scale)</text>
        <text transform={`translate(14 ${geometry.top + plotHeight / 2}) rotate(-90)`} textAnchor="middle" fill="#a9bfbc" fontSize="12">Magnitude (Ω)</text>
      </svg>
    </div>
  );
}


export function ColePlaneChart({ left, right }: ChartProps) {
  const { ref, width } = useChartWidth();
  const geometry: PlotGeometry = { width, height: 290, left: 58, right: 18, top: 16, bottom: 48 };
  const plotWidth = width - geometry.left - geometry.right;
  const plotHeight = geometry.height - geometry.top - geometry.bottom;
  const all = [...left, ...right];
  const resistances = all.map((point) => point.resistance_ohm);
  const negReactances = all.map((point) => -point.reactance_ohm);
  const xPadding = Math.max(5, (Math.max(...resistances) - Math.min(...resistances)) * 0.1);
  const yPadding = Math.max(3, (Math.max(...negReactances) - Math.min(...negReactances)) * 0.1);
  const xMin = Math.min(...resistances) - xPadding;
  const xMax = Math.max(...resistances) + xPadding;
  const yMin = Math.max(0, Math.min(...negReactances) - yPadding);
  const yMax = Math.max(...negReactances) + yPadding;
  const x = (point: BioimpedanceFrequencyPoint) => geometry.left + ((point.resistance_ohm - xMin) / (xMax - xMin)) * plotWidth;
  const y = (point: BioimpedanceFrequencyPoint) => geometry.top + ((yMax + point.reactance_ohm) / (yMax - yMin)) * plotHeight;
  const xTicks = Array.from({ length: 5 }, (_, index) => xMin + ((xMax - xMin) * index) / 4);
  const yTicks = Array.from({ length: 5 }, (_, index) => yMin + ((yMax - yMin) * index) / 4);

  return (
    <div ref={ref}>
      <Legend />
      <svg width="100%" height={geometry.height} viewBox={`0 0 ${width} ${geometry.height}`} role="img" aria-labelledby="cole-title cole-desc">
        <title id="cole-title">Bilateral Cole plane</title>
        <desc id="cole-desc">Resistance in ohms against explicitly negated reactance in ohms for the simulated bilateral sweep.</desc>
        {yTicks.map((tick) => {
          const tickY = geometry.top + ((yMax - tick) / (yMax - yMin)) * plotHeight;
          return <g key={tick}><line x1={geometry.left} x2={width - geometry.right} y1={tickY} y2={tickY} stroke="rgba(140,167,164,.13)" /><text x={geometry.left - 9} y={tickY + 4} textAnchor="end" fill="#8ca7a4" fontSize="11">{tick.toFixed(0)}</text></g>;
        })}
        {xTicks.map((tick) => <text key={tick} x={geometry.left + ((tick - xMin) / (xMax - xMin)) * plotWidth} y={geometry.height - 25} textAnchor="middle" fill="#8ca7a4" fontSize="11">{tick.toFixed(0)}</text>)}
        <line x1={geometry.left} x2={width - geometry.right} y1={geometry.top + plotHeight} y2={geometry.top + plotHeight} stroke="rgba(170,196,192,.35)" />
        <line x1={geometry.left} x2={geometry.left} y1={geometry.top} y2={geometry.top + plotHeight} stroke="rgba(170,196,192,.35)" />
        <path d={path(left, x, y)} fill="none" stroke="var(--aqua)" strokeWidth="2" />
        <path d={path(right, x, y)} fill="none" stroke="#8ed3f3" strokeWidth="2" />
        {left.map((point) => <circle key={`l-${point.frequency_hz}`} cx={x(point)} cy={y(point)} r="3.5" fill="var(--aqua)"><title>{`Left: R ${point.resistance_ohm.toFixed(2)} Ω, -X ${(-point.reactance_ohm).toFixed(2)} Ω`}</title></circle>)}
        {right.map((point) => <circle key={`r-${point.frequency_hz}`} cx={x(point)} cy={y(point)} r="3.5" fill="#8ed3f3"><title>{`Right: R ${point.resistance_ohm.toFixed(2)} Ω, -X ${(-point.reactance_ohm).toFixed(2)} Ω`}</title></circle>)}
        <text x={geometry.left + plotWidth / 2} y={geometry.height - 4} textAnchor="middle" fill="#a9bfbc" fontSize="12">Resistance (Ω)</text>
        <text transform={`translate(14 ${geometry.top + plotHeight / 2}) rotate(-90)`} textAnchor="middle" fill="#a9bfbc" fontSize="12">−Reactance (Ω)</text>
      </svg>
    </div>
  );
}

