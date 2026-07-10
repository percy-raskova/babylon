/**
 * The cockpit shell — CSS-grid AppShell replacing the B1 placeholder
 * regions (spec-110 B3 stage 2). Five persistent regions: StatusBar
 * (col-span-3), Outliner, Map, Dock, BottomStrip (col-span-3). The
 * bottom-strip row collapses to a thin strip via `ui.bottomStripCollapsed`
 * — its content stays mounted (see `BottomStrip.tsx`).
 */

import { useStore } from "@/store";
import { StatusBar } from "./StatusBar";
import { Outliner } from "./Outliner";
import { MapPanel } from "./MapPanel";
import { RightDock } from "./RightDock";
import { BottomStrip } from "./BottomStrip";

interface AppShellProps {
  gameId: string;
}

export function AppShell({ gameId }: AppShellProps): React.JSX.Element {
  const bottomStripCollapsed = useStore((s) => s.ui.bottomStripCollapsed);

  return (
    <div
      className="grid h-screen w-screen grid-cols-[240px_1fr_320px] bg-void text-bone"
      style={{ gridTemplateRows: `48px 1fr ${bottomStripCollapsed ? "32px" : "200px"}` }}
    >
      <StatusBar gameId={gameId} />
      <Outliner gameId={gameId} />
      <MapPanel gameId={gameId} />
      <RightDock gameId={gameId} />
      <BottomStrip gameId={gameId} />
    </div>
  );
}
