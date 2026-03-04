/**
 * IndicatorChip — displays a single metric with urgency-colored value.
 *
 * Per spec FR-022 and research.md R-009: three-tier urgency coloring
 * (SILVER normal, warning-amber warning, CRIMSON critical).
 */

import { formatIndicatorValue, getIndicatorUrgency } from "@/lib/lensDefinitions";
import type { IndicatorDefinition } from "@/types/game";

interface IndicatorChipProps {
  definition: IndicatorDefinition;
  value: number;
  previousValue?: number;
}

/** Map urgency level to Tailwind color classes using constitutional palette. */
const URGENCY_CLASSES: Record<string, string> = {
  normal: "text-silver",
  warning: "text-gold",
  critical: "text-crimson",
};

export function IndicatorChip({ definition, value, previousValue }: IndicatorChipProps) {
  const urgency = getIndicatorUrgency(value, definition.thresholds);
  const formatted = formatIndicatorValue(value, definition.format);
  const colorClass = URGENCY_CLASSES[urgency];

  // Delta arrow
  let deltaIndicator: string | null = null;
  if (previousValue !== undefined) {
    const delta = value - previousValue;
    if (Math.abs(delta) > 0.001) {
      deltaIndicator = delta > 0 ? "\u2191" : "\u2193";
    }
  }

  return (
    <div
      className="flex flex-col items-center gap-0.5 px-2 py-1 min-w-[80px]"
      title={definition.label + ": " + formatted + (definition.unit ? " " + definition.unit : "")}
    >
      <span className="text-[10px] text-ash uppercase tracking-wider">{definition.label}</span>
      <span className={`text-sm font-mono font-semibold ${colorClass}`}>
        {formatted}
        {deltaIndicator && (
          <span
            className="text-[10px] ml-0.5"
            aria-label={deltaIndicator === "\u2191" ? "increasing" : "decreasing"}
          >
            {deltaIndicator}
          </span>
        )}
      </span>
    </div>
  );
}
