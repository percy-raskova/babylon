/**
 * Target picker — flat list of `VerbTarget`s, grouped when the config's
 * targets carry a `group` (e.g. Aid's Communities/Organizations split).
 *
 * FR-116-4.4: rows also render per-target expected-delta chips when the
 * backend produced real resolver-parity numbers for this target.
 */

import type { VerbTarget } from "@/lib/verbs";

interface TargetPickerProps {
  targets: VerbTarget[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** One compact ▲/▼ chip for a non-zero expected delta — null otherwise
 *  (the same honest-null convention as VerbForm's preview DeltaChip). */
function TargetDeltaChip({
  value,
  label,
}: {
  value: number | undefined;
  label: string;
}): React.JSX.Element | null {
  if (value === undefined || !Number.isFinite(value) || value === 0) return null;
  const up = value > 0;
  return (
    <span
      data-testid="target-delta"
      title={`${label}: ${up ? "+" : ""}${value}`}
      className={`font-mono text-[9px] ${up ? "text-accent-gold" : "text-accent-crimson"}`}
    >
      {up ? "▲" : "▼"}
      {label} {up ? "+" : "-"}
      {parseFloat(Math.abs(value).toPrecision(3))}
    </span>
  );
}

export function TargetPicker({
  targets,
  loading,
  error,
  selectedId,
  onSelect,
}: TargetPickerProps): React.JSX.Element {
  if (loading) {
    return <p className="text-[11px] text-ash">Loading targets…</p>;
  }
  if (error) {
    return (
      <p role="alert" className="text-[11px] text-laser">
        {error}
      </p>
    );
  }
  if (targets.length === 0) {
    return <p className="text-[11px] italic text-shroud">No eligible targets.</p>;
  }

  return (
    <div className="flex max-h-40 flex-col gap-1 overflow-y-auto" data-testid="target-picker">
      {targets.map((t) => (
        <button
          key={t.id}
          onClick={() => onSelect(t.id)}
          className={`flex items-center justify-between rounded border px-2 py-1 text-left text-[11px] ${
            t.id === selectedId
              ? "border-spire bg-spire/10 text-spire"
              : "border-rebar text-bone hover:border-wet-steel"
          }`}
        >
          <span className="truncate">{t.label}</span>
          <span className="ml-2 flex shrink-0 items-center gap-1.5">
            <TargetDeltaChip value={t.expectedDeltas?.consciousness} label="CI" />
            <TargetDeltaChip value={t.expectedDeltas?.heat} label="Heat" />
            {t.group && <span className="text-[9px] text-ash">{t.group}</span>}
          </span>
        </button>
      ))}
    </div>
  );
}
