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
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { ObjectivesTracker } from "@/components/objectives/ObjectivesTracker";
import { useObjectives } from "@/hooks/useObjectives";
import { KeyHints } from "./KeyHints";

interface ObjectivesTrayProps {
  gameId: string;
}

export function ObjectivesTray({ gameId }: ObjectivesTrayProps): React.JSX.Element {
  const objectivesOpen = useStore((s) => s.ui.chrome.objectivesOpen);
  const toggleObjectives = useStore((s) => s.ui.toggleObjectives);
  const { data } = useObjectives(gameId);
  const activeCount = data.objectives.filter((o) => o.status === "active").length;

  return (
    <FloatingPanel
      anchor="free"
      title={`Objectives (${activeCount})`}
      collapsed={!objectivesOpen}
      onToggle={toggleObjectives}
      width={280}
      testId="objectives-tray"
    >
      <ObjectivesTracker gameId={gameId} />
      <KeyHints />
    </FloatingPanel>
  );
}
