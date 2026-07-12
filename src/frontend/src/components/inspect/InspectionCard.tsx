/**
 * InspectionCard — one resolved `InspectionFrame` (architecture.md §2.1):
 * title, kind badge, loading/error/no-data states (Constitution III.11),
 * pin toggle, and — for `org`/`hex` subjects — the "act" read/write
 * symmetry link (DESIGN_BIBLE.md §4: "any card stating a changeable fact
 * links to the verb that changes it").
 *
 * The "act" link is deliberately minimal: it opens the ActionDock's
 * composer (`ui.toggleComposer`) without pre-selecting an org/target. A
 * fuller deep-link needs a store action to preset the composer's acting
 * org / target (e.g. `actions.presetTarget(kind, id)`) — out of this
 * lane's ownership (`components/action/*` composer internals are frozen
 * per architecture.md §5 Lane F) and not built here.
 */

import { useStore } from "@/store";
import type { InspectionRef, InspectionRefKind } from "@/types/inspection";
import type { InspectionFrame } from "@/store/slices/inspectSlice";
import { FormulaCard } from "./FormulaCard";

const ACTIONABLE_KINDS: ReadonlySet<InspectionRefKind> = new Set(["org", "hex"]);

interface InspectionCardProps {
  frame: InspectionFrame;
  canDrill: boolean;
  onDrill: (ref: InspectionRef) => void;
  onTogglePin: () => void;
}

export function InspectionCard({
  frame,
  canDrill,
  onDrill,
  onTogglePin,
}: InspectionCardProps): React.JSX.Element {
  const toggleComposer = useStore((s) => s.ui.toggleComposer);
  const title = frame.data?.title ?? frame.ref.label ?? frame.ref.id;

  return (
    <div className="flex flex-col gap-2" data-testid="inspection-card">
      <div className="flex items-center justify-between gap-2 border-b border-rebar pb-1.5">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[12px] font-semibold text-spire">{title}</span>
          <span className="text-[9px] uppercase tracking-widest text-ash">{frame.ref.kind}</span>
        </div>
        <div className="flex items-center gap-1">
          {ACTIONABLE_KINDS.has(frame.ref.kind) && (
            <button
              type="button"
              onClick={() => toggleComposer()}
              data-testid="inspection-act"
              className="rounded border border-rebar px-1.5 py-0.5 text-[9px] uppercase tracking-widest text-fog hover:border-spire hover:text-spire"
            >
              Act
            </button>
          )}
          <button
            type="button"
            onClick={onTogglePin}
            aria-pressed={frame.pinned}
            data-testid="inspection-pin"
            className={`rounded border px-1.5 py-0.5 text-[9px] uppercase tracking-widest ${
              frame.pinned ? "border-spire text-spire" : "border-rebar text-fog"
            }`}
          >
            Pin
          </button>
        </div>
      </div>

      {frame.loading && <p className="text-[11px] text-ash">Loading…</p>}
      {frame.error !== null && (
        <p role="alert" className="text-[11px] text-laser">
          {frame.error}
        </p>
      )}
      {!frame.loading && frame.error === null && frame.data === null && (
        <p className="text-[11px] italic text-shroud" data-testid="inspection-no-data">
          No data returned for this selection.
        </p>
      )}
      {!frame.loading && frame.error === null && frame.data !== null && (
        <FormulaCard node={frame.data} canDrill={canDrill} onDrill={onDrill} />
      )}

      {!canDrill && (
        <p className="text-[10px] italic text-shroud" data-testid="depth-limit-notice">
          Depth limit reached — this is as far as the trail goes.
        </p>
      )}
    </div>
  );
}
