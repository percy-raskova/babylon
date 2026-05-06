/**
 * Stat — label + value pair with optional tooltip.
 *
 * Used across all inspector panels and org detail headers.
 * Never shows averaged-agent stats (per v2 anti-pattern rules).
 */

import { BblLabel } from "./BblLabel";
import { BblData } from "./BblData";
import { BblTooltip } from "./BblTooltip";

interface StatProps {
  label: string;
  value: string;
  color: string;
  tooltip?: string;
  /** If false, wrapping BblTooltip is skipped (parent provides it). */
  wrap?: boolean;
}

export function Stat({ label, value, color, tooltip, wrap = true }: StatProps) {
  const inner = (
    <div className="flex flex-col items-start gap-0.5">
      <BblLabel>{label}</BblLabel>
      <BblData color={color} size={12}>
        {value}
      </BblData>
    </div>
  );

  if (!wrap) return inner;
  return tooltip ? <BblTooltip text={tooltip}>{inner}</BblTooltip> : inner;
}
