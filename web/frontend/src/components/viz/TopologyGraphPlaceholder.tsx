/**
 * TopologyGraphPlaceholder — SVG placeholder for the force-directed social graph.
 *
 * Renders a network diagram with nodes (orgs/communities) and colored edges,
 * representing the eventual d3-force topology view for the Analysis page.
 */

import { ORGS, COMMUNITIES, EDGES, CLASS_COLORS, EDGE_COLORS } from "@/fixtures/v2-mock-data";

interface TopologyGraphPlaceholderProps {
  className?: string;
}

export function TopologyGraphPlaceholder({ className = "" }: TopologyGraphPlaceholderProps) {
  // Layout nodes in a circular arrangement
  const allNodes = [
    ...ORGS.map((o) => ({
      id: o.id,
      label: o.short,
      color: CLASS_COLORS[o.class_character] ?? "#787878",
      type: "org" as const,
      size: o.player_controlled ? 14 : 10,
    })),
    ...COMMUNITIES.slice(0, 3).map((c) => ({
      id: c.id,
      label: c.name.split(" ").slice(0, 2).join(" "),
      color: CLASS_COLORS[c.dominant_class] ?? "#787878",
      type: "community" as const,
      size: 8,
    })),
  ];

  const cx = 250;
  const cy = 175;
  const radius = 120;

  const nodePositions = allNodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / allNodes.length - Math.PI / 2;
    return {
      ...n,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    };
  });

  const posMap = new Map(nodePositions.map((n) => [n.id, n]));

  // Resolve edges to positions
  const edgeLines = EDGES.filter((e) => posMap.has(e.source) || posMap.has(e.target))
    .map((e) => {
      const src = posMap.get(e.source);
      const tgt = posMap.get(e.target);
      if (!src || !tgt) return null;
      return { ...e, x1: src.x, y1: src.y, x2: tgt.x, y2: tgt.y };
    })
    .filter(Boolean) as ((typeof EDGES)[0] & { x1: number; y1: number; x2: number; y2: number })[];

  return (
    <div
      className={`relative flex items-center justify-center overflow-hidden rounded-lg border border-soot bg-void ${className}`}
    >
      <svg viewBox="0 0 500 350" className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="nodeGlow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Edges */}
        {edgeLines.map((e) => (
          <line
            key={e.id}
            x1={e.x1}
            y1={e.y1}
            x2={e.x2}
            y2={e.y2}
            stroke={EDGE_COLORS[e.type] ?? "#787878"}
            strokeWidth={e.intensity * 3}
            strokeOpacity={0.5}
            strokeDasharray={e.type === "SOLIDARITY" ? "4,4" : undefined}
          />
        ))}

        {/* Edge labels */}
        {edgeLines.map((e) => (
          <text
            key={`label-${e.id}`}
            x={(e.x1 + e.x2) / 2}
            y={(e.y1 + e.y2) / 2 - 4}
            textAnchor="middle"
            className="text-[6px]"
            fill={EDGE_COLORS[e.type] ?? "#787878"}
            opacity={0.6}
          >
            {e.type}
          </text>
        ))}

        {/* Nodes */}
        {nodePositions.map((n) => (
          <g key={n.id}>
            {n.type === "org" ? (
              <circle
                cx={n.x}
                cy={n.y}
                r={n.size}
                fill={n.color}
                fillOpacity={0.2}
                stroke={n.color}
                strokeWidth={1.5}
                filter="url(#nodeGlow)"
              />
            ) : (
              <rect
                x={n.x - n.size}
                y={n.y - n.size}
                width={n.size * 2}
                height={n.size * 2}
                fill={n.color}
                fillOpacity={0.15}
                stroke={n.color}
                strokeWidth={1}
                rx={2}
              />
            )}
            <text
              x={n.x}
              y={n.y + n.size + 10}
              textAnchor="middle"
              className="fill-bone text-[7px] font-semibold"
            >
              {n.label}
            </text>
          </g>
        ))}

        {/* Center label */}
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          className="fill-chassis text-[9px] uppercase tracking-[2px]"
        >
          Social Graph
        </text>

        {/* Watermark */}
        <text
          x="250"
          y="340"
          textAnchor="middle"
          className="fill-chassis text-[8px] uppercase tracking-[4px]"
        >
          Topology · d3-force pending
        </text>
      </svg>
    </div>
  );
}
