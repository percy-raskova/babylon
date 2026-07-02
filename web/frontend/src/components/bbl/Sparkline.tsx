/**
 * Sparkline — compact SVG time-series visualization.
 *
 * Used in the Briefing page sparkline strip and Analysis page.
 * Renders polyline + trailing dot + delta indicator.
 */

import { BblLabel } from "./BblLabel";
import { BblData } from "./BblData";

interface SparklineProps {
  data: number[];
  color?: string;
  w?: number;
  h?: number;
  label?: string;
  value?: number;
}

export function Sparkline({
  data,
  color = "#c8a860",
  w = 100,
  h = 24,
  label,
  value,
}: SparklineProps) {
  // Empty series: keep the label visible with a placeholder value so the
  // metrics strip reads correctly before the first tick lands (live
  // sessions start with no history; hiding the row made the strip vanish).
  if (!data || data.length === 0) {
    if (!label) return null;
    return (
      <div className="flex flex-col gap-0.5">
        <div className="flex items-baseline justify-between">
          <BblLabel>{label}</BblLabel>
          <BblData color={color} size={11}>
            —
          </BblData>
        </div>
        <div style={{ width: w, height: h }} />
      </div>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const step = w / (data.length - 1);

  const pts = data.map((v, i) => `${i * step},${h - ((v - min) / span) * h}`).join(" ");

  const last = data[data.length - 1]!;
  const prev = data.length > 1 ? data[data.length - 2]! : last;
  const delta = last - prev;

  return (
    <div className="flex flex-col gap-0.5">
      {label && (
        <div className="flex items-baseline justify-between">
          <BblLabel>{label}</BblLabel>
          <BblData color={color} size={11}>
            {(value !== undefined ? value : last).toFixed(3)}
          </BblData>
        </div>
      )}
      <svg width={w} height={h} className="block">
        <polyline fill="none" stroke={color} strokeWidth="1.2" points={pts} />
        <circle
          cx={(data.length - 1) * step}
          cy={h - ((last - min) / span) * h}
          r="2"
          fill={color}
        />
        {delta !== 0 && (
          <text
            x={w - 2}
            y={10}
            textAnchor="end"
            fontSize="8"
            fill={delta > 0 ? "#40c040" : "#e06060"}
            fontFamily="var(--font-mono)"
          >
            {delta > 0 ? "▲" : "▼"}
          </text>
        )}
      </svg>
    </div>
  );
}
