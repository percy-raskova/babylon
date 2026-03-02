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
    <div style={styles.container}>
      {/* Top bar */}
      <div style={styles.topBar}>
        <button onClick={onBack} style={styles.backButton}>
          &larr; Games
        </button>
        <div style={styles.tickInfo}>
          {snapshot && (
            <>
              <span style={styles.tickLabel}>Tick</span>
              <span style={styles.tickValue}>{snapshot.tick}</span>
            </>
          )}
        </div>
        <div style={styles.gameId}>{gameId.slice(0, 8)}...</div>
      </div>

      {error && <p style={styles.error}>{error}</p>}

      {loading && !snapshot ? (
        <div style={styles.loading}>Loading game state...</div>
      ) : snapshot ? (
        <div style={styles.layout}>
          {/* Left column: Map + Time Series */}
          <div style={styles.leftCol}>
            <div style={styles.mapPanel}>
              <HexMap snapshot={snapshot} />
            </div>
            <div style={styles.timePanel}>
              <TimeSeriesPanel snapshot={snapshot} />
            </div>
          </div>

          {/* Right column: Actions + Orgs + Results */}
          <div style={styles.rightCol}>
            <div style={styles.actionPanelWrap}>
              <ActionPanel
                actions={available}
                onSubmit={submitAction}
                onResolve={handleResolve}
                resolving={resolving}
              />
            </div>
            <div style={styles.orgPanelWrap}>
              <OrgDashboard snapshot={snapshot} />
            </div>
            {results && results.length > 0 && (
              <div style={styles.resultsPanelWrap}>
                <TickResults
                  results={results}
                  tick={snapshot.tick}
                />
              </div>
            )}
          </div>
        </div>
      ) : (
        <div style={styles.loading}>No state available</div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "0 16px 16px",
    height: "calc(100vh - 49px)",
    display: "flex",
    flexDirection: "column" as const,
    overflow: "hidden",
  },
  topBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 0",
    borderBottom: "1px solid #2a2a3a",
    marginBottom: "12px",
    flexShrink: 0,
  },
  backButton: {
    background: "none",
    border: "1px solid #2a2a3a",
    borderRadius: "6px",
    color: "#888",
    padding: "8px 16px",
    cursor: "pointer",
    fontSize: "14px",
  },
  tickInfo: {
    display: "flex",
    alignItems: "baseline",
    gap: "8px",
  },
  tickLabel: {
    color: "#666",
    fontSize: "13px",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
  },
  tickValue: {
    color: "#c8a860",
    fontSize: "28px",
    fontWeight: 700,
    fontFamily: "monospace",
  },
  gameId: {
    color: "#444",
    fontSize: "12px",
    fontFamily: "monospace",
  },
  error: {
    color: "#e04040",
    fontSize: "13px",
    margin: "0 0 8px",
    flexShrink: 0,
  },
  loading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
    color: "#666",
    fontSize: "16px",
  },
  layout: {
    display: "grid",
    gridTemplateColumns: "1fr 360px",
    gap: "12px",
    flex: 1,
    overflow: "hidden",
  },
  leftCol: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "12px",
    overflow: "hidden",
  },
  mapPanel: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "12px",
    flex: 2,
    overflow: "hidden",
    minHeight: 0,
  },
  timePanel: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "12px",
    flex: 1,
    overflow: "hidden",
    minHeight: 0,
  },
  rightCol: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "12px",
    overflow: "hidden",
  },
  actionPanelWrap: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "12px",
    flexShrink: 0,
    maxHeight: "280px",
    overflow: "auto",
  },
  orgPanelWrap: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "12px",
    flex: 1,
    overflow: "hidden",
    minHeight: 0,
  },
  resultsPanelWrap: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "12px",
    flexShrink: 0,
    maxHeight: "300px",
    overflow: "auto",
  },
};
