/**
 * BreakdownBar — proportional composition bar (architecture.md §2.1),
 * absorbing the legacy `components/inspector/ConsciousnessBreakdown.tsx`
 * (consciousness vector today; `wealth_by_class_role` and other
 * composition rows reuse it generically via `InspectionRow.composition`).
 * `entry.color` is a Tailwind color-token class name (e.g. `"text-laser"`)
 * matching the app's existing token vocabulary — converted to the `bg-*`
 * form for the fill segment.
 */

import type { InspectionCompositionEntry } from "@/types/inspection";

interface BreakdownBarProps {
  entries: InspectionCompositionEntry[] | undefined;
}

export function BreakdownBar({ entries }: BreakdownBarProps): React.JSX.Element {
  if (entries === undefined || entries.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="breakdown-no-data">
        no data
      </p>
    );
  }

  const total = entries.reduce((sum, e) => sum + e.value, 0);

  return (
    <div className="flex flex-col gap-1" data-testid="breakdown-bar">
      <div className="flex h-1.5 overflow-hidden rounded-sm bg-rebar">
        {entries.map((e) => (
          <div
            key={e.key}
            style={{ width: total > 0 ? `${(e.value / total) * 100}%` : 0 }}
            className={(e.color ?? "text-bone").replace("text-", "bg-")}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {entries.map((e) => (
          <div key={e.key} className="flex items-center gap-1 text-[10px]">
            <span className={e.color ?? "text-bone"}>{e.key}</span>
            <span className="font-mono text-ash">{e.value.toFixed(3)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
