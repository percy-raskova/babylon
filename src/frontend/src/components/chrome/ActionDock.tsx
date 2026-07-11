/**
 * ActionDock — bottom-center dock (architecture §1.2's `RightDock`
 * disperse row, Actions tab → "bottom-center verb bar; clicking a verb
 * opens `ActionComposer` in a `FloatingPanel`"; Design Bible §5.1: "≤3
 * primary verbs at first contact + labeled 'more' (Shneiderman
 * progressive disclosure)").
 *
 * Two pieces:
 *  1. `action-dock-bar` — an always-visible compact bar of the first three
 *     *engine-wired* verbs (`SUPPORTED_VERBS`, Spec 061 FR-025) plus a
 *     labeled "More" button. This is the only per-verb legality signal any
 *     live API exposes today — there is no per-org/per-target eligibility
 *     endpoint, so "legal" here means "has an engine handler", not
 *     "currently actionable for the selected org". Buttons show their
 *     static cost hint (`cost_label`) visibly, per Bible §5.1's "verbs show
 *     live cost/eligibility on the button" — honest affordance over a
 *     fabricated one.
 *  2. The `ActionComposer` FloatingPanel (unchanged internals — the flat
 *     9-verb grid is Article V's, not this dock's, and stays frozen) that
 *     every bar button opens via `ui.chrome.composerOpen`. v1 keeps
 *     `composerOpen` true by default (`uiSlice`, Lane A) so verb submission
 *     stays a one-step flow for `verb-submit.spec.ts`, which drives
 *     `action-composer`/`verb-grid` directly on page load.
 *
 * NOT implemented — bulk-apply escape hatch (Bible §5.1 "bulk-apply escape
 * hatch for multi-territory orders"): `TargetPicker`/`VerbForm` hold a
 * single `targetId` (frozen internals, architecture §5 Lane F note) and
 * `actions.submit` POSTs one action per call with no batch endpoint. Adding
 * "apply to all eligible" would require editing those frozen files or
 * duplicating their state machine here; per the task brief this is
 * documented as a gap, not faked.
 *
 * Keeps `region-dock` (architecture §6 testid-contract risk — real-loop.
 * spec.ts, owned by Lane G, still asserts it) — now on the dock's outer
 * wrapper rather than the composer's own panel, since the dock is no
 * longer a single FloatingPanel.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { ActionComposer } from "@/components/action/ActionComposer";
import { SUPPORTED_VERBS } from "@/lib/verb-config";
import { keyButtonClass } from "./installerKit";
import { KeyHints } from "./KeyHints";

interface ActionDockProps {
  gameId: string;
}

const PRIMARY_VERBS = SUPPORTED_VERBS.slice(0, 3);

export function ActionDock({ gameId }: ActionDockProps): React.JSX.Element {
  const composerOpen = useStore((s) => s.ui.chrome.composerOpen);
  const toggleComposer = useStore((s) => s.ui.toggleComposer);

  function openComposer(): void {
    if (!composerOpen) toggleComposer();
  }

  return (
    <div data-testid="region-dock" className="flex flex-col items-center gap-1.5">
      <div
        data-testid="action-dock-bar"
        className="pointer-events-auto flex items-center gap-1.5 border-2 border-ksbc-muted-1 bg-plate/90 px-2 py-1.5 backdrop-blur-sm shadow-[6px_6px_0_#000]"
      >
        {PRIMARY_VERBS.map((v) => (
          <button
            key={v.verb}
            onClick={openComposer}
            title={v.desc}
            data-testid={`action-dock-verb-${v.verb}`}
            className={keyButtonClass(
              false,
              "flex flex-col items-center gap-0.5 px-2 py-1 text-center",
            )}
          >
            <span className="text-sm">{v.glyph}</span>
            <span className="text-[9px] uppercase tracking-widest">{v.label}</span>
            <span className="text-[8px] text-ksbc-muted-2">{v.cost_label}</span>
          </button>
        ))}
        <button
          onClick={openComposer}
          aria-expanded={composerOpen}
          data-testid="action-dock-more"
          className={keyButtonClass(composerOpen, "self-stretch px-2 text-[9px]")}
        >
          More
        </button>
      </div>

      <FloatingPanel
        anchor="free"
        title="Actions"
        collapsed={!composerOpen}
        onToggle={toggleComposer}
        testId="action-composer-panel"
      >
        <ActionComposer gameId={gameId} />
        <KeyHints />
      </FloatingPanel>
    </div>
  );
}
