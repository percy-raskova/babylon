/**
 * OutlinerOverlay — chrome stub hosting the unchanged `Outliner`
 * (architecture §1.2 migrate row; the always-on index of the player's
 * organizations, per the Design Bible §5.1 Stellaris idiom). A
 * `FloatingPanel` (anchor="left") wrapping `Outliner` verbatim — its
 * internals are Lane F's territory, not restructured here.
 *
 * Deliberately does NOT repeat `Outliner`'s own `region-outliner` testid on
 * this wrapper (that would create two elements matching the same testid);
 * `Outliner`'s inner `<nav>` stays the single frozen `region-outliner`
 * landmark.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { Outliner } from "@/components/shell/Outliner";

interface OutlinerOverlayProps {
  gameId: string;
}

export function OutlinerOverlay({ gameId }: OutlinerOverlayProps): React.JSX.Element {
  const outlinerOpen = useStore((s) => s.ui.chrome.outlinerOpen);
  const toggleOutliner = useStore((s) => s.ui.toggleOutliner);

  return (
    <FloatingPanel
      anchor="left"
      title="Outliner"
      collapsed={!outlinerOpen}
      onToggle={toggleOutliner}
      width={240}
      testId="outliner-overlay"
    >
      <Outliner gameId={gameId} />
    </FloatingPanel>
  );
}
