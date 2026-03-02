/**
 * Game view component.
 *
 * Displays the game state as formatted JSON with action controls.
 * Phase 7 will replace this with HexMap, ActionPanel, etc.
 */

import { useState } from "react";
import { useGameState } from "@/hooks/useGameState";
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
        <button
          onClick={handleResolve}
          disabled={resolving || loading}
          style={styles.resolveButton}
        >
          {resolving ? "Resolving..." : "Resolve Tick"}
        </button>
      </div>

      {error && <p style={styles.error}>{error}</p>}

      <div style={styles.panels}>
        {/* State panel */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Game State</h3>
          {loading && !snapshot ? (
            <p style={styles.loading}>Loading...</p>
          ) : snapshot ? (
            <pre style={styles.json}>
              {JSON.stringify(snapshot, null, 2)}
            </pre>
          ) : (
            <p style={styles.loading}>No state available</p>
          )}
        </div>

        {/* Actions panel */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Available Actions</h3>
          {available.length === 0 ? (
            <p style={styles.emptyActions}>No actions available</p>
          ) : (
            <div style={styles.actionList}>
              {available.map((action, i) => (
                <button
                  key={`${action.org_id}-${action.verb}-${i}`}
                  onClick={() =>
                    submitAction({
                      org_id: action.org_id,
                      verb: action.verb,
                      action_type: action.action_type,
                    })
                  }
                  style={styles.actionButton}
                >
                  <span style={styles.actionOrg}>{action.org_id}</span>
                  <span style={styles.actionVerb}>{action.verb}</span>
                  {action.cost !== undefined && (
                    <span style={styles.actionCost}>
                      Cost: {action.cost.toFixed(1)}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Results display */}
          {results && results.length > 0 && (
            <>
              <h3 style={{ ...styles.panelTitle, marginTop: "24px" }}>
                Tick Results
              </h3>
              <pre style={styles.json}>
                {JSON.stringify(results, null, 2)}
              </pre>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: "1400px",
    margin: "0 auto",
    padding: "16px 24px",
    height: "100vh",
    display: "flex",
    flexDirection: "column" as const,
  },
  topBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 0",
    borderBottom: "1px solid #2a2a3a",
    marginBottom: "16px",
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
  resolveButton: {
    background: "#c8a860",
    color: "#0a0a0f",
    border: "none",
    borderRadius: "8px",
    padding: "10px 24px",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
  },
  error: {
    color: "#e04040",
    fontSize: "13px",
    margin: "0 0 12px",
  },
  panels: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
    flex: 1,
    overflow: "hidden",
  },
  panel: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "16px",
    overflow: "auto",
  },
  panelTitle: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#c8a860",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
    marginBottom: "12px",
  },
  json: {
    fontSize: "12px",
    color: "#a0a0a0",
    fontFamily: "monospace",
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-all" as const,
    lineHeight: 1.5,
    margin: 0,
  },
  loading: {
    color: "#666",
    fontSize: "14px",
  },
  emptyActions: {
    color: "#666",
    fontSize: "14px",
  },
  actionList: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "8px",
  },
  actionButton: {
    background: "#0e0e18",
    border: "1px solid #2a2a3a",
    borderRadius: "6px",
    padding: "10px 14px",
    cursor: "pointer",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    color: "#e0e0e0",
    fontSize: "13px",
    width: "100%",
  },
  actionOrg: {
    fontWeight: 600,
    color: "#80b0e0",
  },
  actionVerb: {
    fontWeight: 500,
    color: "#c8a860",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  actionCost: {
    color: "#888",
    fontSize: "12px",
  },
};
