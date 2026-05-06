/**
 * Gauge — resource gauge with progress bar.
 *
 * Used in the TopBar for CL/SL readouts. Shows label, current/max value,
 * and a filled progress bar.
 */

import { BblLabel } from "./BblLabel";
import { BblData } from "./BblData";
import { BblTooltip } from "./BblTooltip";

interface GaugeProps {
  label: string;
  value: number;
  max: number;
  color: string;
  tooltip?: string;
}

export function Gauge({ label, value, max, color, tooltip }: GaugeProps) {
  const pct = Math.min(1, value / max);
  const inner = (
    <div className="flex min-w-[70px] flex-col gap-0.5">
      <div className="flex items-baseline justify-between">
        <BblLabel>{label}</BblLabel>
        <BblData color={color} size={10}>
          {value.toFixed(1)}
          <span className="text-chassis">/{max}</span>
        </BblData>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-soot">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct * 100}%`, background: color }}
        />
      </div>
    </div>
  );

  return tooltip ? <BblTooltip text={tooltip}>{inner}</BblTooltip> : inner;
}
