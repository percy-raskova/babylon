/**
 * ImperialCircuitFlow — hand-rolled SVG mini-Sankey for the 4-node imperial
 * circuit (Program 17 Wave 1 / W1.6): Periphery Proletariat -> Comprador
 * Bourgeoisie -> Core Bourgeoisie -> Labor Aristocracy. Renders only the
 * nodes/links the backend's `circuit_flows` actually carries — a scenario
 * missing a role (wayne_county has no `comprador_bourgeoisie` class) simply
 * omits that node/link, never a fabricated placeholder (Constitution III.11).
 * No chart library: positioned circles + directed ribbon lines whose
 * stroke-width scales with `value_flow` (same plain-hex-color convention as
 * `bbl/Sparkline`, no new npm deps).
 */

import type { CircuitFlows } from "@/types/inspection";

const ROLE_LABELS: Record<string, string> = {
  periphery_proletariat: "Periphery Proletariat",
  comprador_bourgeoisie: "Comprador",
  core_bourgeoisie: "Core Bourgeoisie",
  labor_aristocracy: "Labor Aristocracy",
};

const WIDTH = 280;
const HEIGHT = 88;
const NODE_Y = 40;
const NODE_RADIUS = 5;
const MARGIN = 34;
const MIN_STROKE = 1.5;
const MAX_STROKE = 9;
const SPIRE = "#4dd9e6";
const BONE = "#d8dce0";
const ASH = "#5e6470";
const SHROUD = "#3d4250";

interface ImperialCircuitFlowProps {
  data: CircuitFlows;
}

/** Even horizontal spread across the diagram width for `count` nodes. */
function xFor(index: number, count: number): number {
  if (count <= 1) return WIDTH / 2;
  return MARGIN + (index * (WIDTH - 2 * MARGIN)) / (count - 1);
}

/** Ribbon stroke-width proportional to `value_flow`, floored at MIN_STROKE
 * so a real-but-zero flow (a freshly-seeded tick-0 edge) still renders as a
 * visible line rather than vanishing. */
function strokeWidthFor(value: number, maxValue: number): number {
  if (maxValue <= 0) return MIN_STROKE;
  return MIN_STROKE + (Math.max(0, value) / maxValue) * (MAX_STROKE - MIN_STROKE);
}

export function ImperialCircuitFlow({ data }: ImperialCircuitFlowProps): React.JSX.Element {
  const { nodes, links } = data;
  const positions = new Map<string, number>(nodes.map((n, i) => [n.id, xFor(i, nodes.length)]));
  const maxFlow = links.reduce((max, l) => Math.max(max, l.value_flow), 0);

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width="100%"
      height={HEIGHT}
      data-testid="imperial-circuit-flow"
      role="img"
      aria-label="Imperial circuit value flow"
    >
      {links.map((link) => {
        const x1 = positions.get(link.source_id);
        const x2 = positions.get(link.target_id);
        if (x1 === undefined || x2 === undefined) return null;
        return (
          <line
            key={`${link.source_id}-${link.target_id}`}
            data-testid={`circuit-flow-link-${link.source_id}-${link.target_id}`}
            x1={x1}
            y1={NODE_Y}
            x2={x2}
            y2={NODE_Y}
            stroke={SPIRE}
            strokeWidth={strokeWidthFor(link.value_flow, maxFlow)}
            strokeOpacity={0.55}
            strokeLinecap="round"
          />
        );
      })}
      {nodes.map((node) => {
        const x = positions.get(node.id) ?? 0;
        return (
          <g key={node.id} data-testid={`circuit-flow-node-${node.id}`}>
            <circle cx={x} cy={NODE_Y} r={NODE_RADIUS} fill={BONE} />
            <text x={x} y={NODE_Y - 12} textAnchor="middle" fontSize={8} fill={ASH}>
              {ROLE_LABELS[node.role] ?? node.role}
            </text>
            <text x={x} y={NODE_Y + 20} textAnchor="middle" fontSize={7} fill={SHROUD}>
              {node.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
