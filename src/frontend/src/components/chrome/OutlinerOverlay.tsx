/**
 * OutlinerOverlay — chrome stub hosting the unchanged `Outliner`
 * (architecture §1.2 migrate row; the always-on index of the player's
 * organizations, per the Design Bible §5.1 Stellaris idiom). A
 * `FloatingPanel` (anchor="left") wrapping `Outliner` verbatim — its
 * internals are Lane F's territory, not restructured here.
 *
 * Collapses to an icon rail rather than a same-width empty strip: since
 * `FloatingPanel`'s `width`/`title` are caller-supplied props (its internals
 * are Lane A's, frozen here), the rail effect is achieved entirely from this
 * call site — a narrow width + a glyph title when collapsed.
 *
 * Deliberately does NOT repeat `Outliner`'s own `region-outliner` testid on
 * this wrapper (that would create two elements matching the same testid);
 * `Outliner`'s inner `<nav>` stays the single frozen `region-outliner`
 * landmark.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { Outliner } from "@/components/shell/Outliner";
import { KeyHints } from "./KeyHints";

interface OutlinerOverlayProps {
  gameId: string;
}

const OPEN_WIDTH = 240;
const RAIL_WIDTH = 44;

export function OutlinerOverlay({ gameId }: OutlinerOverlayProps): React.JSX.Element {
  const outlinerOpen = useStore((s) => s.ui.chrome.outlinerOpen);
  const toggleOutliner = useStore((s) => s.ui.toggleOutliner);

  return (
    <FloatingPanel
      anchor="left"
      title={outlinerOpen ? "Outliner" : "☰"}
      collapsed={!outlinerOpen}
      onToggle={toggleOutliner}
      width={outlinerOpen ? OPEN_WIDTH : RAIL_WIDTH}
      testId="outliner-overlay"
    >
      <Outliner gameId={gameId} />
      {outlinerOpen && <KeyHints />}
    </FloatingPanel>
  );
}
