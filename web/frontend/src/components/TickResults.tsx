/**
 * Tick results display component.
 *
 * Shows action results after tick resolution with success/failure indicators.
 */

import type { ActionResultData } from "@/types/game";

interface TickResultsProps {
  results: ActionResultData[];
  tick: number;
}

export function TickResults({ results, tick }: TickResultsProps) {
  if (results.length === 0) {
    return (
      <div style={styles.container}>
        <h3 style={styles.title}>Tick {tick} Results</h3>
        <p style={styles.empty}>No results for this tick</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Tick {tick} Results</h3>
      <div style={styles.list}>
        {results.map((result, i) => (
          <div
            key={`${result.org_id}-${result.action_type}-${i}`}
            style={{
              ...styles.resultCard,
              borderLeftColor: result.success ? "#40c040" : "#e04040",
            }}
          >
            <div style={styles.resultHeader}>
              <span style={styles.orgId}>{result.org_id}</span>
              <span
                style={{
                  ...styles.outcome,
                  color: result.success ? "#40c040" : "#e04040",
                }}
              >
                {result.success ? "SUCCESS" : "FAILED"}
              </span>
            </div>
            <div style={styles.actionInfo}>
              <span style={styles.actionType}>{result.action_type}</span>
              {result.target_id && (
                <span style={styles.target}>
                  &rarr; {result.target_id}
                </span>
              )}
            </div>
            <div style={styles.metrics}>
              <MetricPill
                label="Initiative"
                value={result.initiative_score}
              />
              <MetricPill label="Cost" value={result.action_cost} />
              {result.consciousness_delta != null && (
                <MetricPill
                  label="Consciousness"
                  value={result.consciousness_delta}
                  signed
                />
              )}
              {result.heat_delta != null && (
                <MetricPill
                  label="Heat"
                  value={result.heat_delta}
                  signed
                />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricPill({
  label,
  value,
  signed = false,
}: {
  label: string;
  value: number;
  signed?: boolean;
}) {
  const display = signed
    ? `${value >= 0 ? "+" : ""}${value.toFixed(2)}`
    : value.toFixed(2);

  const color =
    signed && value !== 0
      ? value > 0
        ? "#60c060"
        : "#e06060"
      : "#aaa";

  return (
    <span style={{ ...pillStyles.pill, color }}>
      <span style={pillStyles.label}>{label}</span> {display}
    </span>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    height: "100%",
  },
  title: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#c8a860",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
    marginBottom: "12px",
    flexShrink: 0,
  },
  empty: {
    color: "#666",
    fontSize: "14px",
    textAlign: "center" as const,
  },
  list: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "8px",
    overflow: "auto",
    flex: 1,
  },
  resultCard: {
    background: "#0e0e18",
    border: "1px solid #2a2a3a",
    borderLeft: "3px solid",
    borderRadius: "4px",
    padding: "10px 14px",
  },
  resultHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "6px",
  },
  orgId: {
    fontWeight: 600,
    color: "#80b0e0",
    fontSize: "13px",
  },
  outcome: {
    fontSize: "11px",
    fontWeight: 700,
    letterSpacing: "1px",
  },
  actionInfo: {
    display: "flex",
    gap: "8px",
    marginBottom: "8px",
    fontSize: "13px",
  },
  actionType: {
    color: "#c8a860",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    fontSize: "12px",
  },
  target: {
    color: "#888",
    fontSize: "12px",
  },
  metrics: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: "8px",
  },
};

const pillStyles: Record<string, React.CSSProperties> = {
  pill: {
    fontSize: "11px",
    fontFamily: "monospace",
    background: "#141420",
    borderRadius: "3px",
    padding: "2px 6px",
  },
  label: {
    color: "#666",
    marginRight: "4px",
  },
};
