/**
 * ObjectivesTray — chrome stub hosting `ObjectivesTracker` verbatim
 * (architecture §1.2's `RightDock` disperse row, Objectives tab).
 *
 * `anchor="free"` — `AppShell` composes the shared right-column wrapper
 * (stacked with `EventTray` per the §1.1 layout diagram); this component
 * doesn't self-position a full-height right edge.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { ObjectivesTracker } from "@/components/objectives/ObjectivesTracker";

interface ObjectivesTrayProps {
  gameId: string;
}

export function ObjectivesTray({ gameId }: ObjectivesTrayProps): React.JSX.Element {
  const objectivesOpen = useStore((s) => s.ui.chrome.objectivesOpen);
  const toggleObjectives = useStore((s) => s.ui.toggleObjectives);

  return (
    <FloatingPanel
      anchor="free"
      title="Objectives"
      collapsed={!objectivesOpen}
      onToggle={toggleObjectives}
      width={280}
      testId="objectives-tray"
    >
      <ObjectivesTracker gameId={gameId} />
    </FloatingPanel>
  );
}
