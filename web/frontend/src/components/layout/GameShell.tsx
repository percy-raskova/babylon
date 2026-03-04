/**
 * Game shell — full-viewport container composing TopBar, map area,
 * collapsible right sidebar, and collapsible bottom panel.
 */

import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router";
import { useGameState } from "@/hooks/useGameState";
import { useUIStore } from "@/stores/uiStore";
import { TopBar } from "@/components/layout/TopBar";
import { RightPanel } from "@/components/layout/RightPanel";
import { BottomPanel } from "@/components/layout/BottomPanel";
import { LensBar } from "@/components/layout/LensBar";
import { usePersistentUI } from "@/hooks/usePersistentUI";
import { DeckGLMap } from "@/components/map/DeckGLMap";
import { ActionComposer } from "@/components/action/ActionComposer";
import { Inspector } from "@/components/inspector/Inspector";
import { TickResults } from "@/components/TickResults";
import { TimeSeries } from "@/components/charts/TimeSeries";
import { GraphView } from "@/components/graph/GraphView";
import { EventLog } from "@/components/events/EventLog";
import { NotificationToast } from "@/components/events/NotificationToast";
import { EndgameOverlay } from "@/components/layout/EndgameOverlay";
import { detectEndgame } from "@/utils/endgame";
import type { ActionResultData, EndgameData } from "@/types/game";

interface GameShellProps {
  username: string;
  onBack: () => void;
  onLogout: () => void;
}

export function GameShell({ username, onBack, onLogout }: GameShellProps) {
  const { id: gameId = "" } = useParams<{ id: string }>();
  const { snapshot, loading, error, submitAction, resolveTick } = useGameState(gameId);
  const [results, setResults] = useState<ActionResultData[] | null>(null);
  const [resolving, setResolving] = useState(false);
  const [endgame, setEndgame] = useState<EndgameData | null>(null);
  const bottomTab = useUIStore((s) => s.bottomTab);
  const notifications = useUIStore((s) => s.notifications);
  usePersistentUI();
  const clearBreadcrumbs = useUIStore((s) => s.clearBreadcrumbs);
  const setSelectedHex = useUIStore((s) => s.setSelectedHex);
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);

  // Escape key clears selection and breadcrumbs
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        clearBreadcrumbs();
        setSelectedHex(null);
        setSelectedNode(null);
      }
    },
    [clearBreadcrumbs, setSelectedHex, setSelectedNode],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [handleEscape]);

  async function handleResolve() {
    setResolving(true);
    const tickResults = await resolveTick();
    setResults(tickResults);
    setResolving(false);

    const detected = detectEndgame(snapshot);
    if (detected) setEndgame(detected);
  }

  if (loading && !snapshot) {
    return (
      <div className="flex h-screen items-center justify-center text-silver">
        Loading game state...
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="flex h-screen items-center justify-center text-silver">
        No state available
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-void">
      {/* Endgame notification overlay */}
      {endgame && (
        <EndgameOverlay endgame={endgame} onDismiss={() => setEndgame(null)} onBack={onBack} />
      )}

      {/* Top bar */}
      <TopBar
        snapshot={snapshot}
        gameId={gameId}
        username={username}
        resolving={resolving}
        onResolve={handleResolve}
        onBack={onBack}
        onLogout={onLogout}
      />

      {error && <p className="shrink-0 px-4 py-1 text-[13px] text-crimson">{error}</p>}

      {/* Main area: map + right panel */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Center: map + bottom panel */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Map + critical notification overlay */}
          <div className="relative flex-1 overflow-hidden p-3">
            <div className="h-full rounded-lg border border-wet-concrete bg-dark-metal">
              <DeckGLMap snapshot={snapshot} />
            </div>
            {/* Critical event toast overlay */}
            <NotificationToast
              events={notifications.filter((e) => e.severity === "critical" && !e.read)}
            />
          </div>

          {/* Lens selector */}
          <LensBar />

          {/* Bottom panel */}
          <BottomPanel>
            {bottomTab === "timeseries" && <TimeSeries snapshot={snapshot} />}
            {bottomTab === "events" && <EventLog snapshot={snapshot} />}
            {bottomTab === "graph" && <GraphView snapshot={snapshot} />}
            {bottomTab === "notifications" && <EventLog snapshot={snapshot} grouped />}
          </BottomPanel>
        </div>

        {/* Right sidebar */}
        <RightPanel>
          <div className="max-h-[360px] shrink-0 overflow-auto rounded-lg border border-wet-concrete bg-dark-metal p-3">
            <ActionComposer
              snapshot={snapshot}
              onSubmit={submitAction}
              onResolve={handleResolve}
              resolving={resolving}
            />
          </div>
          <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-wet-concrete bg-dark-metal p-3">
            <Inspector snapshot={snapshot} />
          </div>
          {results && results.length > 0 && (
            <div className="max-h-[300px] shrink-0 overflow-auto rounded-lg border border-wet-concrete bg-dark-metal p-3">
              <TickResults results={results} tick={snapshot.tick} />
            </div>
          )}
        </RightPanel>
      </div>
    </div>
  );
}
