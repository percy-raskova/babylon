/**
 * ObjectivesTray — chrome stub hosting `ObjectivesTracker` verbatim
 * (architecture §1.2's `RightDock` disperse row, Objectives tab).
 *
 * `anchor="free"` — `AppShell` composes the shared right-column wrapper
 * (stacked with `EventTray` per the §1.1 layout diagram); this component
 * doesn't self-position a full-height right edge.
 *
 * Badge = active objective count (Design Bible §5.1 "collapsible, badge =
 * active objective count"). Baked into `FloatingPanel`'s `title` string
 * (its header has no separate badge slot — internals are Lane A's, frozen
 * here) so it's visible whether the tray is expanded or collapsed to its
 * header strip. Reuses `useObjectives` directly rather than threading a
 * count prop through `ObjectivesTracker` (also frozen-adjacent — it's a
 * `components/objectives/**` file this lane owns, but its own props are
 * `{gameId}` only elsewhere; duplicating the read-only hook call mirrors
 * the existing `Outliner`/`MapPanel` shared-panel pattern, see
 * `Outliner.tsx`'s docstring).
 *
 * Spec-116 FR-116-5 — the mercy affordance: an "ACCEPT THIS OUTCOME" button
 * appears above the tracker once `endgame_progress.locked` is true (the
 * per-tick HUD block `resolve_tick` stashes onto `world.snapshot`). Clicking
 * it calls `world.acceptOutcome`, which POSTs `/accept-outcome/` and
 * refetches the endgame panel — the pre-existing `worldSlice` outcome
 * watcher (not duplicated here) then opens the chronicle takeover.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { RAIL_RIGHT_W } from "./layout";
import { keyButtonUrgentClass } from "./installerKit";
import { ObjectivesTracker } from "@/components/objectives/ObjectivesTracker";
import { useObjectives } from "@/hooks/useObjectives";

interface ObjectivesTrayProps {
  gameId: string;
}

export function ObjectivesTray({ gameId }: ObjectivesTrayProps): React.JSX.Element {
  const objectivesOpen = useStore((s) => s.ui.chrome.objectivesOpen);
  const toggleObjectives = useStore((s) => s.ui.toggleObjectives);
  const { data } = useObjectives(gameId);
  const activeCount = data.objectives.filter((o) => o.status === "active").length;

  const locked = useStore((s) => s.world.snapshot?.endgame_progress?.locked ?? false);
  const acceptOutcome = useStore((s) => s.world.acceptOutcome);

  return (
    <FloatingPanel
      anchor="free"
      title={`Objectives (${activeCount})`}
      collapsed={!objectivesOpen}
      onToggle={toggleObjectives}
      width={RAIL_RIGHT_W}
      testId="objectives-tray"
    >
      {locked && (
        <button
          type="button"
          onClick={() => void acceptOutcome(gameId)}
          data-testid="accept-outcome"
          className={keyButtonUrgentClass("mb-2 w-full px-2.5 py-1.5 text-[10px]")}
        >
          ACCEPT THIS OUTCOME — end the campaign
        </button>
      )}
      <ObjectivesTracker gameId={gameId} />
    </FloatingPanel>
  );
}
