/**
 * A single top-bar metric chip with Constitution III.11 null-honesty:
 * `null`/`undefined` renders as a visibly distinct "no data" state, never
 * a fabricated `0`.
 *
 * "Every number explains itself" starts here (DESIGN_BIBLE.md §4, last
 * bullet): when `metric` is supplied, the chip becomes a probe — clicking
 * it pushes a `metric`-kind `InspectionRef` (scope `"global"` unless
 * `scope` overrides it) onto the InspectionStack. `metric`/`scope` are
 * additive and optional so existing call sites keep rendering a plain,
 * non-clickable chip until their owner threads a metric name through
 * (`chrome/TopBar.tsx` is Lane A's file, out of this lane's ownership —
 * its three `StatChip` call sites still pass no `metric` prop today).
 */

import { useStore } from "@/store";

interface StatChipProps {
  label: string;
  value: number | null | undefined;
  format: (v: number) => string;
  colorClassName?: string;
  /** Explainable metric name (`web/game/provenance.py::METRIC_PROVENANCE` key) — makes the chip clickable. */
  metric?: string;
  /** Explain scope, canonical string form (`"global"` | `"hex:<h3>"` | `"org:<id>"`). Defaults to `"global"`. */
  scope?: string;
}

export function StatChip({
  label,
  value,
  format,
  colorClassName = "text-bone",
  metric,
  scope = "global",
}: StatChipProps): React.JSX.Element {
  const hasData = value !== null && value !== undefined;
  const push = useStore((s) => s.inspect.push);

  const content = (
    <>
      <span className="text-[9px] uppercase tracking-widest text-ksbc-muted-2">{label}</span>
      <span
        className={`font-mono text-[11px] font-semibold ${
          hasData ? colorClassName : "italic text-ksbc-muted-1"
        }`}
      >
        {hasData ? format(value) : "no data"}
      </span>
    </>
  );

  if (metric === undefined) {
    return (
      <div
        className="flex items-center gap-1.5 border-2 border-ksbc-muted-1 bg-plate px-2.5 py-1"
        data-testid={`stat-${label.toLowerCase()}`}
      >
        {content}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => push({ kind: "metric", id: metric, scope, label })}
      className="flex items-center gap-1.5 border-2 border-ksbc-muted-1 bg-plate px-2.5 py-1 transition-colors hover:border-accent-crimson"
      data-testid={`stat-${label.toLowerCase()}`}
    >
      {content}
    </button>
  );
}
