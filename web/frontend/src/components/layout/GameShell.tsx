/**
 * Game shell — lean briefing view with map, sparkline strip, and navigation.
 *
 * Phase 6: Removed ActionComposer, TimeSeries, EventLog, GraphView,
 * BottomPanel, RightPanel. These now live at their own routes.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "react-router";
import { useGameState } from "@/hooks/useGameState";
import { useUIStore } from "@/stores/uiStore";
import { TopBar } from "@/components/layout/TopBar";
import { LensBar } from "@/components/layout/LensBar";
import { SparklineStrip } from "@/components/charts/SparklineStrip";
import { NavigationStrip } from "@/components/layout/NavigationStrip";
import { usePersistentUI } from "@/hooks/usePersistentUI";
import { DeckGLMap } from "@/components/map/DeckGLMap";
import { ResourcePanel } from "@/components/ResourcePanel";
import { TrapIndicator } from "@/components/TrapIndicator";
import { TickResults } from "@/components/TickResults";
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
  const { snapshot, loading, error, resolveTick } = useGameState(gameId);
  const [results, setResults] = useState<ActionResultData[] | null>(null);
  const [resolving, setResolving] = useState(false);
  const [endgame, setEndgame] = useState<EndgameData | null>(null);
  const notifications = useUIStore((s) => s.notifications);
  usePersistentUI();
  const clearBreadcrumbs = useUIStore((s) => s.clearBreadcrumbs);
  const setSelectedHex = useUIStore((s) => s.setSelectedHex);
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);

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

  // Escape key clears selection
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

  // Dismiss tick results
  function dismissResults() {
    setResults(null);
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
      {/* Endgame overlay */}
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

      {/* Resource bar */}
      <div className="shrink-0 px-3">
        <ResourcePanel playerOrg={playerOrg} />
      </div>

      {/* Trap warnings */}
      <div className="shrink-0 px-3">
        <TrapIndicator traps={snapshot.traps} />
      </div>

      {/* Navigation strip */}
      <NavigationStrip />

      {/* Map */}
      <div className="relative min-h-0 flex-1 overflow-hidden p-3">
        <div className="h-full rounded-lg border border-wet-concrete bg-dark-metal">
          <ErrorBoundary fallbackLabel="Map">
            <DeckGLMap snapshot={snapshot} />
          </ErrorBoundary>
        </div>
        {/* Critical event toast */}
        <NotificationToast
          events={notifications.filter((e) => e.severity === "critical" && !e.read)}
        />
      </div>

      {/* Lens bar */}
      <LensBar />

      {/* Sparkline strip */}
      <SparklineStrip />

      {/* Tick results toast (dismissible) */}
      {results && results.length > 0 && (
        <div className="shrink-0 border-t border-wet-concrete bg-dark-metal p-3">
          <div className="flex items-start justify-between">
            <TickResults results={results} tick={snapshot.tick} />
            <button
              onClick={dismissResults}
              className="ml-2 text-xs text-ash hover:text-gold"
              aria-label="Dismiss tick results"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
