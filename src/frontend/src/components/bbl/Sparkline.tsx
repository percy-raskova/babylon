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

/** Placeholder row for an empty series — keeps the label visible so the
 * metrics strip reads correctly before the first tick lands. */
function SparklinePlaceholder({
  label,
  color,
  w,
  h,
}: {
  label: string;
  color: string;
  w: number;
  h: number;
}) {
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

/** Last two points of a non-empty series. `?? 0`/`?? last` satisfy
 * noUncheckedIndexedAccess without a non-null assertion — callers only
 * invoke this once `data.length >= 1` is already established. */
function trailingValues(data: number[]): { last: number; prev: number } {
  const last = data[data.length - 1] ?? 0;
  const prev = data.length > 1 ? (data[data.length - 2] ?? last) : last;
  return { last, prev };
}

export function Sparkline({
  data,
  color = "#c8a860",
  w = 100,
  h = 24,
  label,
  value,
}: SparklineProps) {
  if (!data || data.length === 0) {
    return label ? <SparklinePlaceholder label={label} color={color} w={w} h={h} /> : null;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const step = w / (data.length - 1);

  const pts = data.map((v, i) => `${i * step},${h - ((v - min) / span) * h}`).join(" ");

  const { last, prev } = trailingValues(data);
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
