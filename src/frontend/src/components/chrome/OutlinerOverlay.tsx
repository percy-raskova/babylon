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
// Widths live in chrome/layout.ts (the single source of truth the map-control
// safe-area offsets derive from) — never hard-code them here, or the lens bar
// silently slides under this rail again (spec-113 Phase V).
import { RAIL_LEFT_W, RAIL_LEFT_COLLAPSED_W } from "./layout";

interface OutlinerOverlayProps {
  gameId: string;
}

export function OutlinerOverlay({ gameId }: OutlinerOverlayProps): React.JSX.Element {
  const outlinerOpen = useStore((s) => s.ui.chrome.outlinerOpen);
  const toggleOutliner = useStore((s) => s.ui.toggleOutliner);

  return (
    <FloatingPanel
      anchor="left"
      title={outlinerOpen ? "Outliner" : "☰"}
      collapsed={!outlinerOpen}
      onToggle={toggleOutliner}
      width={outlinerOpen ? RAIL_LEFT_W : RAIL_LEFT_COLLAPSED_W}
      testId="outliner-overlay"
    >
      <Outliner gameId={gameId} />
      {outlinerOpen && <KeyHints />}
    </FloatingPanel>
  );
}
