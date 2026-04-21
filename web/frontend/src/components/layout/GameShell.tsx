/**
 * Game shell — full-viewport container composing TopBar, map area,
 * collapsible right sidebar, and collapsible bottom panel.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
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
import { ResourcePanel } from "@/components/ResourcePanel";
import { TrapIndicator } from "@/components/TrapIndicator";
import { TickResults } from "@/components/TickResults";
import { TimeSeries } from "@/components/charts/TimeSeries";
import { GraphView } from "@/components/graph/GraphView";
import { EventLog } from "@/components/events/EventLog";
import { NotificationToast } from "@/components/events/NotificationToast";
import { EndgameOverlay } from "@/components/layout/EndgameOverlay";
import { detectEndgame } from "@/utils/endgame";
import type { ActionResultData, EndgameData } from "@/types/game";
import { ErrorBoundary } from "@/components/ErrorBoundary";

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
  const graphPanelOpen = useUIStore((s) => s.graphPanelOpen);
  const graphPanelWidth = useUIStore((s) => s.graphPanelWidth);
  const toggleGraphPanel = useUIStore((s) => s.toggleGraphPanel);

  // Find the player org for the resource panel
  const playerOrg = useMemo(() => {
    if (!snapshot) return null;
    return (
      snapshot.organizations.find(
        (o) => o.class_character === "proletarian" && o.org_type === "civil_society_org",
      ) ??
      snapshot.organizations[0] ??
      null
    );
  }, [snapshot]);

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
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-void text-center">
        <p className="text-base font-medium text-silver">No state available</p>
        {error && <p className="text-sm text-crimson">{error}</p>}
        <p className="max-w-sm text-xs text-ash">
          This usually means the session expired or you aren&apos;t logged in. Try logging in again.
        </p>
        <button
          onClick={onBack}
          className="rounded border border-wet-concrete px-4 py-2 text-sm text-silver hover:border-gold"
        >
          ← Back to Games
        </button>
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

      {error && (
        <p className="shrink-0 px-4 py-1 text-[13px] text-crimson" data-testid="error-banner">
          {error}
        </p>
      )}

      {/* Vanguard economy resource bar */}
      <div className="shrink-0 px-3">
        <ResourcePanel playerOrg={playerOrg} />
      </div>

      {/* Trap deviation warnings */}
      <div className="shrink-0 px-3">
        <TrapIndicator traps={snapshot.traps} />
      </div>

      {/* Main area: graph panel (left) + map (center) + right panel */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left panel: Topology graph (Option A — peer panel) */}
        {graphPanelOpen && (
          <div
            className="flex shrink-0 flex-col overflow-hidden border-r border-wet-concrete"
            style={{ width: graphPanelWidth }}
          >
            <div className="flex items-center justify-between border-b border-wet-concrete bg-void px-3 py-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-ash">
                Topology
              </span>
              <button
                onClick={toggleGraphPanel}
                className="text-[10px] text-ash hover:text-gold"
                title="Collapse graph panel"
                data-testid="collapse-graph-panel"
              >
                ◀
              </button>
            </div>
            <div className="relative min-h-0 flex-1 overflow-hidden">
              <div className="absolute inset-0 p-2">
                <ErrorBoundary fallbackLabel="Topology Graph">
                  <GraphView snapshot={snapshot} />
                </ErrorBoundary>
              </div>
            </div>
          </div>
        )}

        {/* Graph panel collapsed toggle */}
        {!graphPanelOpen && (
          <button
            onClick={toggleGraphPanel}
            className="flex w-6 shrink-0 items-center justify-center border-r border-wet-concrete bg-void text-[10px] text-ash hover:bg-dark-metal hover:text-gold"
            title="Expand graph panel"
            data-testid="expand-graph-panel"
          >
            ▶
          </button>
        )}

        {/* Center: map + bottom panel */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Map + critical notification overlay */}
          <div className="relative flex-1 overflow-hidden p-3">
            <div className="h-full rounded-lg border border-wet-concrete bg-dark-metal">
              <ErrorBoundary fallbackLabel="Map">
                <DeckGLMap snapshot={snapshot} />
              </ErrorBoundary>
            </div>
            {/* Critical event toast overlay */}
            <NotificationToast
              events={notifications.filter((e) => e.severity === "critical" && !e.read)}
            />
          </div>

          {/* Lens selector */}
          <LensBar />

          {/* Bottom panel (graph tab removed — now in left panel) */}
          <BottomPanel>
            {bottomTab === "timeseries" && (
              <ErrorBoundary fallbackLabel="Time Series">
                <TimeSeries snapshot={snapshot} />
              </ErrorBoundary>
            )}
            {bottomTab === "events" && (
              <ErrorBoundary fallbackLabel="Event Log">
                <EventLog snapshot={snapshot} />
              </ErrorBoundary>
            )}
            {bottomTab === "notifications" && (
              <ErrorBoundary fallbackLabel="Notifications">
                <EventLog snapshot={snapshot} grouped />
              </ErrorBoundary>
            )}
          </BottomPanel>
        </div>

        {/* Right sidebar */}
        <RightPanel>
          <div className="max-h-[360px] shrink-0 overflow-auto rounded-lg border border-wet-concrete bg-dark-metal p-3">
            <ActionComposer snapshot={snapshot} onSubmit={submitAction} resolving={resolving} />
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
