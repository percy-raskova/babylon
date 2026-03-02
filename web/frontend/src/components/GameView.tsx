/**
 * Game view component.
 *
 * Main game interface with HexMap, ActionPanel, OrgDashboard,
 * TickResults, and TimeSeriesPanel.
 */

import { useState } from "react";
import { useGameState } from "@/hooks/useGameState";
import { HexMap } from "@/components/HexMap";
import { ActionPanel } from "@/components/ActionPanel";
import { OrgDashboard } from "@/components/OrgDashboard";
import { TickResults } from "@/components/TickResults";
import { TimeSeriesPanel } from "@/components/TimeSeriesPanel";
import type { ActionResultData } from "@/types/game";

interface GameViewProps {
  gameId: string;
  onBack: () => void;
}

export function GameView({ gameId, onBack }: GameViewProps) {
  const { snapshot, available, loading, error, submitAction, resolveTick } =
    useGameState(gameId);
  const [results, setResults] = useState<ActionResultData[] | null>(null);
  const [resolving, setResolving] = useState(false);

  async function handleResolve() {
    setResolving(true);
    const tickResults = await resolveTick();
    setResults(tickResults);
    setResolving(false);
  }

  return (
    <div className="flex h-[calc(100vh-49px)] flex-col overflow-hidden px-4 pb-4">
      {/* Top bar */}
      <div className="mb-3 flex shrink-0 items-center justify-between border-b border-wet-concrete py-3">
        <button
          onClick={onBack}
          className="rounded-md border border-wet-concrete px-4 py-2 text-sm text-silver hover:border-silver"
        >
          &larr; Games
        </button>
        <div className="flex items-baseline gap-2">
          {snapshot && (
            <>
              <span className="text-[13px] uppercase tracking-wider text-ash">
                Tick
              </span>
              <span className="font-mono text-[28px] font-bold text-gold">
                {snapshot.tick}
              </span>
            </>
          )}
        </div>
        <div className="font-mono text-xs text-ash">{gameId.slice(0, 8)}...</div>
      </div>

      {error && (
        <p className="mb-2 shrink-0 text-[13px] text-crimson">{error}</p>
      )}

      {loading && !snapshot ? (
        <div className="flex flex-1 items-center justify-center text-silver">
          Loading game state...
        </div>
      ) : snapshot ? (
        <div className="grid flex-1 grid-cols-[1fr_360px] gap-3 overflow-hidden">
          {/* Left column: Map + Time Series */}
          <div className="flex flex-col gap-3 overflow-hidden">
            <div className="flex-[2] overflow-hidden rounded-lg border border-wet-concrete bg-dark-metal p-3">
              <HexMap snapshot={snapshot} />
            </div>
            <div className="flex-1 overflow-hidden rounded-lg border border-wet-concrete bg-dark-metal p-3">
              <TimeSeriesPanel snapshot={snapshot} />
            </div>
          </div>

          {/* Right column: Actions + Orgs + Results */}
          <div className="flex flex-col gap-3 overflow-hidden">
            <div className="max-h-[280px] shrink-0 overflow-auto rounded-lg border border-wet-concrete bg-dark-metal p-3">
              <ActionPanel
                actions={available}
                onSubmit={submitAction}
                onResolve={handleResolve}
                resolving={resolving}
              />
            </div>
            <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-wet-concrete bg-dark-metal p-3">
              <OrgDashboard snapshot={snapshot} />
            </div>
            {results && results.length > 0 && (
              <div className="max-h-[300px] shrink-0 overflow-auto rounded-lg border border-wet-concrete bg-dark-metal p-3">
                <TickResults results={results} tick={snapshot.tick} />
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center text-silver">
          No state available
        </div>
      )}
    </div>
  );
}
