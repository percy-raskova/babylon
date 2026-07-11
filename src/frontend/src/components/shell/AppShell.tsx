/**
 * The Living Map shell (spec-113, architecture §0/§1.1) — replaces the
 * B1-era CSS-grid AppShell that pinned five fixed regions. Three stacked
 * layers:
 *
 * - Layer 0 — `MapStage`: `DeckGLMap` at `absolute inset-0`, always
 *   mounted, the only scroll/drag surface.
 * - Layer 1 — Chrome: a `pointer-events-none` full-viewport overlay whose
 *   children (top bar, outliner, event tray, action dock, ...)
 *   individually re-enable `pointer-events-auto` (via `FloatingPanel`).
 *   Map interactions pass through the gaps.
 * - Layer 2 — `TakeoverOverlay` (unchanged; already renders fixed over
 *   everything, already map-first-compatible).
 *
 * `components/inspect/InspectionStack` (Lane C, not yet built) mounts
 * inside the chrome layer, anchored left-of-tray, once it exists — see
 * the comment below for where.
 */

import { MapStage } from "./MapStage";
import { TopBar } from "@/components/chrome/TopBar";
import { OutlinerOverlay } from "@/components/chrome/OutlinerOverlay";
import { InspectionStack } from "@/components/inspect/InspectionStack";
import { EventTray } from "@/components/chrome/EventTray";
import { ObjectivesTray } from "@/components/chrome/ObjectivesTray";
import { ActionDock } from "@/components/chrome/ActionDock";
import { BottomDrawer } from "@/components/chrome/BottomDrawer";
import { EventToasts } from "@/components/chrome/EventToasts";
import { CriticalEventModal } from "@/components/chrome/CriticalEventModal";
import { TakeoverOverlay } from "@/components/takeovers/TakeoverOverlay";

interface AppShellProps {
  gameId: string;
}

export function AppShell({ gameId }: AppShellProps): React.JSX.Element {
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-void text-bone">
      {/* Layer 0 — the persistent map, full-bleed, always mounted. */}
      <MapStage gameId={gameId} />

      {/* Layer 1 — chrome. Individual FloatingPanel instances re-enable
          pointer-events-auto; everything else in this container passes
          clicks/drags straight through to the map underneath. */}
      <div data-testid="chrome-layer" className="pointer-events-none absolute inset-0">
        <TopBar gameId={gameId} />
        <OutlinerOverlay gameId={gameId} />

        {/* InspectionStack (Lane C) — anchored left-of-tray; it renders
            nothing (returns null) when the stack is empty, so it needs
            no visibility-toggling wrapper here. */}
        <InspectionStack gameId={gameId} />

        <div className="pointer-events-none absolute bottom-2 right-2 top-14 flex flex-col gap-2">
          <div className="pointer-events-auto min-h-0 flex-1">
            <EventTray gameId={gameId} />
          </div>
          <div className="pointer-events-auto shrink-0">
            <ObjectivesTray gameId={gameId} />
          </div>
        </div>

        <div className="pointer-events-auto absolute bottom-2 left-1/2 -translate-x-1/2">
          <ActionDock gameId={gameId} />
        </div>

        <BottomDrawer gameId={gameId} />

        <EventToasts gameId={gameId} />
        <CriticalEventModal gameId={gameId} />
      </div>

      {/* Layer 2 — takeovers, unchanged. */}
      <TakeoverOverlay gameId={gameId} />
    </div>
  );
}
