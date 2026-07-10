/**
 * Target picker — flat list of `VerbTarget`s, grouped when the config's
 * targets carry a `group` (e.g. Aid's Communities/Organizations split).
 */

import type { VerbTarget } from "@/lib/verbs";

interface TargetPickerProps {
  targets: VerbTarget[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
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
          {t.group && <span className="ml-2 shrink-0 text-[9px] text-ash">{t.group}</span>}
        </button>
      ))}
    </div>
  );
}
