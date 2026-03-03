/**
 * Tick results display component.
 *
 * Shows action results after tick resolution with success/failure indicators.
 */

import type { ActionResultData } from "@/types/game";

interface TickResultsProps {
  results: ActionResultData[];
  tick: number;
}

export function TickResults({ results, tick }: TickResultsProps) {
  if (results.length === 0) {
    return (
      <div className="flex h-full flex-col">
        <h3 className="mb-3 shrink-0 text-sm font-semibold uppercase tracking-wider text-gold">
          Tick {tick} Results
        </h3>
        <p className="text-center text-sm text-ash">No results for this tick</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <h3 className="mb-3 shrink-0 text-sm font-semibold uppercase tracking-wider text-gold">
        Tick {tick} Results
      </h3>
      <div className="flex flex-1 flex-col gap-2 overflow-auto">
        {results.map((result, i) => (
          <div
            key={`${result.org_id}-${result.action_type}-${i}`}
            className={`rounded border border-wet-concrete bg-void px-3.5 py-2.5 ${
              result.success
                ? "border-l-[3px] border-l-data-green"
                : "border-l-[3px] border-l-phosphor-red"
            }`}
          >
            <div className="mb-1.5 flex justify-between">
              <span className="text-[13px] font-semibold text-royal-blue">{result.org_id}</span>
              <span
                className={`text-[11px] font-bold tracking-wider ${
                  result.success ? "text-data-green" : "text-phosphor-red"
                }`}
              >
                {result.success ? "SUCCESS" : "FAILED"}
              </span>
            </div>
            <div className="mb-2 flex gap-2 text-[13px]">
              <span className="text-xs uppercase tracking-wider text-gold">
                {result.action_type}
              </span>
              {result.target_id && (
                <span className="text-xs text-ash">&rarr; {result.target_id}</span>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <MetricPill label="Initiative" value={result.initiative_score} />
              <MetricPill label="Cost" value={result.action_cost} />
              {result.consciousness_delta != null && (
                <MetricPill label="Consciousness" value={result.consciousness_delta} signed />
              )}
              {result.heat_delta != null && (
                <MetricPill label="Heat" value={result.heat_delta} signed />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricPill({
  label,
  value,
  signed = false,
}: {
  label: string;
  value: number;
  signed?: boolean;
}) {
  let display = value.toFixed(2);
  if (signed) {
    const prefix = value >= 0 ? "+" : "";
    display = `${prefix}${value.toFixed(2)}`;
  }

  let colorClass = "text-silver";
  if (signed && value !== 0) {
    colorClass = value > 0 ? "text-data-green" : "text-phosphor-red";
  }

  return (
    <span className={`rounded bg-[#141420] px-1.5 py-0.5 font-mono text-[11px] ${colorClass}`}>
      <span className="mr-1 text-ash">{label}</span> {display}
    </span>
  );
}
