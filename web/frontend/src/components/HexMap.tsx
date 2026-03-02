/**
 * Hex map visualization using Leaflet + H3.
 *
 * Renders territory nodes as H3 hexagons on a Leaflet map.
 * Hex color encodes a selectable metric (heat, consciousness, wealth).
 */

import { useCallback, useMemo, useState } from "react";
import type { GameSnapshot, NodeState } from "@/types/game";

/** Color scales for different metrics. */
const COLOR_SCALES: Record<string, (v: number) => string> = {
  heat: (v) => {
    const r = Math.round(40 + v * 200);
    const g = Math.round(40 - v * 30);
    const b = Math.round(60 - v * 40);
    return `rgb(${r},${g},${b})`;
  },
  consciousness: (v) => {
    const r = Math.round(40 + v * 60);
    const g = Math.round(60 + v * 140);
    const b = Math.round(100 + v * 150);
    return `rgb(${r},${g},${b})`;
  },
  wealth: (v) => {
    const r = Math.round(50 + v * 150);
    const g = Math.round(160 + v * 80);
    const b = Math.round(50 + v * 50);
    return `rgb(${r},${g},${b})`;
  },
};

interface HexMapProps {
  snapshot: GameSnapshot;
  onSelectNode?: (nodeId: string) => void;
}

export function HexMap({ snapshot, onSelectNode }: HexMapProps) {
  const [metric, setMetric] = useState<string>("heat");
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const territories = useMemo(() => {
    return Object.entries(snapshot.nodes).filter(
      ([, node]) => node.node_type === "territory",
    );
  }, [snapshot.nodes]);

  const getColor = useCallback(
    (node: NodeState) => {
      const value = Number(node[metric] ?? 0);
      const clamped = Math.max(0, Math.min(1, value));
      const scale = COLOR_SCALES[metric] ?? COLOR_SCALES["heat"]!;
      return scale(clamped);
    },
    [metric],
  );

  return (
    <div style={styles.container}>
      <div style={styles.controls}>
        <span style={styles.label}>Color by:</span>
        {Object.keys(COLOR_SCALES).map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            style={{
              ...styles.metricButton,
              ...(metric === m ? styles.metricActive : {}),
            }}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Grid-based hex display (Leaflet integration deferred to npm install) */}
      <div style={styles.hexGrid}>
        {territories.map(([id, node]) => (
          <button
            key={id}
            onClick={() => onSelectNode?.(id)}
            onMouseEnter={() => setHoveredNode(id)}
            onMouseLeave={() => setHoveredNode(null)}
            style={{
              ...styles.hexCell,
              background: getColor(node),
              border:
                hoveredNode === id
                  ? "2px solid #c8a860"
                  : "1px solid #1a1a2a",
            }}
            title={`${id}: ${metric}=${Number(node[metric] ?? 0).toFixed(2)}`}
          >
            <span style={styles.hexLabel}>
              {String(node["name"] ?? id).slice(0, 8)}
            </span>
          </button>
        ))}
        {territories.length === 0 && (
          <p style={styles.empty}>No territory data available</p>
        )}
      </div>

      {hoveredNode && snapshot.nodes[hoveredNode] && (
        <div style={styles.tooltip}>
          <strong>{hoveredNode}</strong>
          <pre style={styles.tooltipPre}>
            {JSON.stringify(snapshot.nodes[hoveredNode], null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    height: "100%",
    position: "relative" as const,
  },
  controls: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 0",
    flexShrink: 0,
  },
  label: {
    color: "#888",
    fontSize: "12px",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
  },
  metricButton: {
    background: "#0e0e18",
    border: "1px solid #2a2a3a",
    borderRadius: "4px",
    color: "#888",
    padding: "4px 10px",
    fontSize: "12px",
    cursor: "pointer",
  },
  metricActive: {
    background: "#1a1a30",
    borderColor: "#c8a860",
    color: "#c8a860",
  },
  hexGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(80px, 1fr))",
    gap: "4px",
    flex: 1,
    overflow: "auto",
    padding: "8px 0",
  },
  hexCell: {
    aspectRatio: "1",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    transition: "border 0.15s",
    minHeight: "60px",
  },
  hexLabel: {
    fontSize: "10px",
    color: "rgba(255,255,255,0.7)",
    textAlign: "center" as const,
    wordBreak: "break-all" as const,
  },
  empty: {
    color: "#666",
    fontSize: "14px",
    gridColumn: "1 / -1",
    textAlign: "center" as const,
    padding: "32px",
  },
  tooltip: {
    position: "absolute" as const,
    bottom: "8px",
    left: "8px",
    right: "8px",
    background: "#1a1a28",
    border: "1px solid #2a2a3a",
    borderRadius: "6px",
    padding: "10px",
    fontSize: "12px",
    color: "#ccc",
    maxHeight: "200px",
    overflow: "auto",
  },
  tooltipPre: {
    margin: "4px 0 0",
    fontSize: "11px",
    color: "#999",
    whiteSpace: "pre-wrap" as const,
  },
};
