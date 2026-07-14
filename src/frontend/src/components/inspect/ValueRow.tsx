/**
 * ValueRow — one labeled value in an `InspectionCard` (architecture.md
 * §2.1). Constitution III.11 null-honesty: `value === null` always renders
 * "no data", never a fabricated placeholder. Rows carrying a `ref` render
 * the "explain" affordance (underline + chevron) UNLESS `canDrill` is
 * `false` (DESIGN_BIBLE.md §4's content-limited depth cap), in which case
 * the value renders dimmed with a "Depth limit reached" tooltip instead of
 * a click target — Constitution III.11 again: a blocked drill is shown
 * loud, never silently absent.
 *
 * Composition rows (`row.composition`) delegate to `BreakdownBar` instead
 * of a plain value; `row.history` (comparison baseline,
 * DESIGN_BIBLE.md §4 "every stat row shows its comparison baseline")
 * renders a `Sparkline` with realized min/max labeled inline next to it —
 * `bbl/Sparkline` itself has no min/max readout, so that label is rendered
 * here rather than by editing a file outside this lane's ownership.
 *
 * Program 17 Wave 1 additive: `row.circuitFlows` (W1.6) delegates to
 * `ImperialCircuitFlow` instead of a plain value/composition — the 4-node
 * imperial-circuit mini-Sankey. `row.mock` (W1.4) renders a small
 * `MockBadge` next to the label — the owner's mock doctrine, a placeholder
 * value that must never be mistaken for real data.
 */

import { Sparkline } from "@/components/bbl/Sparkline";
import type { BblFormat, InspectionRef, InspectionRow } from "@/types/inspection";
import { BreakdownBar } from "./BreakdownBar";
import { ImperialCircuitFlow } from "./ImperialCircuitFlow";
import { MockBadge } from "./MockBadge";

function formatValue(value: number | string, format: BblFormat): string {
  if (typeof value === "string") return value;
  switch (format) {
    case "integer":
      return Math.round(value).toLocaleString();
    case "decimal2":
      return value.toFixed(2);
    case "decimal3":
      return value.toFixed(3);
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    case "raw":
      return String(value);
  }
}

interface ValueRowProps {
  row: InspectionRow;
  canDrill: boolean;
  onDrill: (ref: InspectionRef) => void;
}

/** The plain label+value row (the common case: no composition/circuitFlows). */
function PlainValueRow({ row, canDrill, onDrill }: ValueRowProps): React.JSX.Element {
  const hasData = row.value !== null;
  const displayValue = row.value !== null ? formatValue(row.value, row.format) : "no data";
  const clickable = row.ref !== undefined && canDrill;
  const blocked = row.ref !== undefined && !canDrill;

  return (
    <div className="flex items-baseline justify-between gap-2 text-[11px]">
      <span className="text-ash">
        {row.label}
        {row.mock === true && (
          <>
            {" "}
            <MockBadge />
          </>
        )}
      </span>
      {clickable ? (
        <button
          type="button"
          onClick={() => row.ref && onDrill(row.ref)}
          data-testid={`explain-${row.label}`}
          className="font-mono text-bone underline decoration-dotted underline-offset-2 hover:text-spire"
        >
          {displayValue} <span aria-hidden="true">&rsaquo;</span>
        </button>
      ) : (
        <span
          className={`font-mono ${hasData ? "text-bone" : "italic text-shroud"} ${
            blocked ? "opacity-50" : ""
          }`}
          title={blocked ? "Depth limit reached" : undefined}
        >
          {displayValue}
        </span>
      )}
    </div>
  );
}

/** Which of the three mutually-exclusive row bodies to render (circuitFlows
 * mini-Sankey / composition BreakdownBar / plain value) — extracted so the
 * choice is a flat if/else chain rather than a nested ternary. */
function RowBody(props: ValueRowProps): React.JSX.Element {
  const { row } = props;
  if (row.circuitFlows !== undefined) {
    return (
      <div className="flex flex-col gap-0.5">
        <span className="text-[11px] text-ash">{row.label}</span>
        <ImperialCircuitFlow data={row.circuitFlows} />
      </div>
    );
  }
  if (row.composition !== undefined) {
    return (
      <div className="flex flex-col gap-0.5">
        <span className="text-[11px] text-ash">{row.label}</span>
        <BreakdownBar entries={row.composition} />
      </div>
    );
  }
  return <PlainValueRow {...props} />;
}

export function ValueRow(props: ValueRowProps): React.JSX.Element {
  const { row } = props;
  return (
    <div className="flex flex-col gap-0.5 py-0.5" data-testid={`value-row-${row.label}`}>
      <RowBody {...props} />

      {row.history && row.history.length > 0 && (
        <div className="flex items-center gap-2" data-testid={`history-${row.label}`}>
          <Sparkline data={row.history} w={80} h={16} />
          <span className="font-mono text-[9px] text-shroud">
            min {Math.min(...row.history).toFixed(2)} / max {Math.max(...row.history).toFixed(2)}
          </span>
        </div>
      )}
    </div>
  );
}
