/**
 * InspectionCard — one resolved `InspectionFrame` (architecture.md §2.1):
 * title, kind badge, loading/error/no-data states (Constitution III.11),
 * pin toggle, and — for `org`/`hex` subjects — the "act" read/write
 * symmetry link (DESIGN_BIBLE.md §4: "any card stating a changeable fact
 * links to the verb that changes it").
 *
 * The "act" link is deliberately minimal: it opens the ActionDock's
 * composer (`ui.toggleComposer`) without pre-selecting an org/target.
 *
 * Track 1 Task 7 (2026-07-18) built the fuller deep-link this docstring
 * used to defer: a resolved `fog`-kind frame (a masked political field's
 * "no fogged dead ends" explanation, see `lib/inspect/adapters/fog.ts`)
 * renders a dedicated "Investigate" CTA — `actions.presetInvestigate` +
 * `ui.openComposer` (unconditional open, never a toggle-shut surprise) —
 * genuinely pre-targeting the composer's INVESTIGATE verb at the masked
 * node. This is real end-to-end: `resolve_investigate`
 * (`src/babylon/engine/actions/investigate.py`) reads `target_id` directly
 * off the graph with no allow-list against the target-discovery endpoint
 * (`get_investigate_targets`, still substantially mocked — Task 9), so a
 * target this CTA presets works even though it likely won't appear
 * highlighted in that endpoint's convenience list — `VerbForm`'s
 * `preset-target-note` is exactly the honesty measure for that gap.
 *
 * Wave 2 W2.5a addition: for a resolved `social_class` node (detected via
 * `hasSurvivalCalculus` — the adapted node carries a "Survival Calculus"
 * section), mounts `SurvivalDuelPanel` beneath `FormulaCard` to supply the
 * historical duel chart the synchronous adapter pipeline can't fetch itself
 * (owner ruling 3: real history endpoint, never client-side accumulation).
 * Needs `gameId`, which `InspectionStack` already threads in but did not
 * previously forward.
 */

import { useStore } from "@/store";
import type { InspectionRef, InspectionRefKind } from "@/types/inspection";
import type { InspectionFrame } from "@/store/slices/inspectSlice";
import { FormulaCard } from "./FormulaCard";
import { SurvivalDuelPanel } from "./SurvivalDuelPanel";
import { hasSurvivalCalculus } from "@/lib/inspect/adapters/node";

const ACTIONABLE_KINDS: ReadonlySet<InspectionRefKind> = new Set(["org", "hex"]);

/** `SurvivalDuelPanel` mounts only once the frame has actually resolved to a
 * `social_class` node and a `gameId` is available to fetch with — extracted
 * so this branching doesn't push `InspectionCard`'s own complexity over the
 * lint ceiling. `null` (not rendering anything) covers every other case:
 * still loading/errored/no-data, a non-social_class subject, or no gameId. */
function survivalDuelSlot(
  frame: InspectionFrame,
  gameId: string | undefined,
): React.JSX.Element | null {
  const resolved = !frame.loading && frame.error === null && frame.data !== null;
  if (!resolved || gameId === undefined || !hasSurvivalCalculus(frame.data)) return null;
  return <SurvivalDuelPanel gameId={gameId} classId={frame.ref.id} />;
}

/** The "HOW to learn it" CTA for a `fog`-kind frame — null for every other
 *  kind, or when the ref's own `inline.nodeId` is missing (honest absence,
 *  never a button that silently has no target). Reads `nodeId`/`nodeName`
 *  straight off `ref.inline` (the same payload `adaptFog` resolved from),
 *  not from `frame.data`, so the CTA works even while a slow resolve is
 *  still loading/erroring. */
function fogInvestigateSlot(
  frame: InspectionFrame,
  presetInvestigate: (targetId: string, targetLabel: string) => void,
  openComposer: () => void,
): React.JSX.Element | null {
  if (frame.ref.kind !== "fog") return null;
  const inline = frame.ref.inline ?? {};
  const nodeId = typeof inline.nodeId === "string" ? inline.nodeId : null;
  if (nodeId === null) return null;
  const nodeName = typeof inline.nodeName === "string" ? inline.nodeName : nodeId;

  return (
    <button
      type="button"
      onClick={() => {
        presetInvestigate(nodeId, nodeName);
        openComposer();
      }}
      data-testid="fog-investigate-link"
      className="self-start rounded border border-rebar px-1.5 py-0.5 text-[9px] uppercase tracking-widest text-fog hover:border-spire hover:text-spire"
    >
      Investigate &rsaquo;
    </button>
  );
}

interface InspectionCardProps {
  frame: InspectionFrame;
  canDrill: boolean;
  onDrill: (ref: InspectionRef) => void;
  onTogglePin: () => void;
  /** Active game session id (Wave 2 W2.5a) — only needed to feed
   * `SurvivalDuelPanel`'s history fetch; omitted callers simply never see
   * that panel (its social_class detection still runs, but nothing renders
   * without a gameId to fetch with). */
  gameId?: string;
}

export function InspectionCard({
  frame,
  canDrill,
  onDrill,
  onTogglePin,
  gameId,
}: InspectionCardProps): React.JSX.Element {
  const toggleComposer = useStore((s) => s.ui.toggleComposer);
  const presetInvestigate = useStore((s) => s.actions.presetInvestigate);
  const openComposer = useStore((s) => s.ui.openComposer);
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

      {survivalDuelSlot(frame, gameId)}
      {fogInvestigateSlot(frame, presetInvestigate, openComposer)}

      {!canDrill && (
        <p className="text-[10px] italic text-shroud" data-testid="depth-limit-notice">
          Depth limit reached — this is as far as the trail goes.
        </p>
      )}
    </div>
  );
}
