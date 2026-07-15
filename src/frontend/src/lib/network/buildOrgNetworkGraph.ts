/**
 * buildOrgNetworkGraph — pure `OrgNetworkPayload` -> graphology `Graph`
 * transform for the Network takeover (AW4-R2). No sigma/DOM/React
 * involved, so it's unit-testable on its own (`buildOrgNetworkGraph.test.ts`).
 *
 * Node size encodes the backend's own real degree centrality
 * (`OrgNetworkPayload.centrality`, `_org_network_centrality` in
 * `web/game/engine_bridge.py`) — never recomputed client-side, Constitution
 * III.11: the frontend renders what the engine/bridge actually measured.
 *
 * Layout is a deterministic circular placement (nodes sorted by id, evenly
 * spaced) rather than an animated/random force simulation: neither
 * `graphology-layout`/`graphology-layout-forceatlas2` nor any other layout
 * package is installed (verified: `ls node_modules | grep graphology`
 * before writing this), and the "ZERO new dependencies" rule rules out
 * adding one. This also satisfies DESIGN_BIBLE §11 law 2/3 (qualities cut,
 * one motion budget per tick) — a network takeover isn't the principal
 * contradiction's pulse, so it gets a static, settled-once picture: the
 * same payload always renders the same picture, with no ambient motion.
 *
 * Colors are literal hex values (not `var(--x)` CSS custom properties)
 * because sigma renders to a canvas/WebGL context, which — like deck.gl's
 * `RGBAColor` tuples in `theme/colors.ts` — needs a resolved color, not a
 * DOM-relative CSS variable reference. The hex values themselves are NOT
 * invented: they are copied verbatim from the `--babylon-*` tokens already
 * ratified in `index.css` (spire/cadre/population/solidarity/ash), the same
 * "reuse the existing token, don't invent a new hue" discipline
 * `EconomyDashboard.tsx`'s `ROLE_CHIP_COLOR` already follows.
 */

import Graph from "graphology";
import type { OrgNetworkPayload, OrgNetworkNode, OrgNetworkEdge } from "@/types/game";

/** Node fill color by `OrgNetworkNode.type` — literal hex copies of the
 *  matching `--babylon-*` token (`index.css`), chosen for the nearest
 *  documented semantic fit: organizations are the network's active agents
 *  (spire, "infrastructure/agency online"); institutions are apparatus/info
 *  (cadre); territories are the geographic/demographic substrate
 *  (population). */
export const NODE_TYPE_COLOR: Record<OrgNetworkNode["type"], string> = {
  organization: "#4dd9e6", // --babylon-spire
  institution: "#6b8fb5", // --babylon-cadre
  territory: "#7a6db8", // --babylon-population
};

/** SOLIDARITY edges render in the mass-line green (--babylon-solidarity) —
 *  the exact terminal `theme/colors.ts`'s `solidarity` data ramp already
 *  ends on — distinct from every other edge mode's neutral default. */
export const SOLIDARITY_EDGE_COLOR = "#5fbf7a"; // --babylon-solidarity
/** Default edge color for every non-SOLIDARITY mode — a neutral, muted
 *  --babylon-ash, never a fabricated per-mode palette for modes this lens
 *  has no ratified encoding for. */
export const DEFAULT_EDGE_COLOR = "#5e6470"; // --babylon-ash

const MIN_NODE_SIZE = 4;
const MAX_NODE_SIZE = 20;
const SOLIDARITY_EDGE_SIZE = 3;
const DEFAULT_EDGE_SIZE = 1;
const LAYOUT_RADIUS = 100;

/**
 * Deterministic circular layout: node ids sorted lexicographically, placed
 * evenly around a fixed-radius circle. Pure function of the id set — no
 * randomness, no prior-frame state — so the same payload always produces
 * the same picture (rebuilding twice yields identical coordinates).
 */
export function computeCircularLayout(nodeIds: string[]): Map<string, { x: number; y: number }> {
  const sorted = [...nodeIds].sort();
  const n = sorted.length;
  const positions = new Map<string, { x: number; y: number }>();
  sorted.forEach((id, i) => {
    const angle = (2 * Math.PI * i) / n;
    positions.set(id, {
      x: LAYOUT_RADIUS * Math.cos(angle),
      y: LAYOUT_RADIUS * Math.sin(angle),
    });
  });
  return positions;
}

/** Map a real (backend-supplied) degree-centrality value in [0, 1] to a
 *  sigma node pixel size, monotonically. Out-of-band input clamps rather
 *  than distorting the scale. */
export function nodeSizeFromDegree(degree: number): number {
  const clamped = Math.max(0, Math.min(1, degree));
  return MIN_NODE_SIZE + clamped * (MAX_NODE_SIZE - MIN_NODE_SIZE);
}

/** The node types actually present in this payload, sorted — the legend's
 *  honesty contract: never render a swatch for a type/mode the data doesn't
 *  actually contain. */
export function presentNodeTypes(payload: OrgNetworkPayload): OrgNetworkNode["type"][] {
  return [...new Set(payload.nodes.map((n) => n.type))].sort();
}

/** The edge modes actually present in this payload, sorted, deduped — see
 *  `presentNodeTypes`'s honesty contract. */
export function presentEdgeModes(payload: OrgNetworkPayload): string[] {
  return [...new Set(payload.edges.map((e) => e.mode))].sort();
}

/** A short human label for a node — falls back to the raw id when the
 *  attributes bag carries no `name` (never fabricates a display name). */
function nodeLabel(node: OrgNetworkNode): string {
  const name = node.attributes["name"];
  return typeof name === "string" && name.length > 0 ? name : node.id;
}

function addGraphNode(
  graph: Graph,
  node: OrgNetworkNode,
  degree: number,
  position: { x: number; y: number },
): void {
  graph.addNode(node.id, {
    label: nodeLabel(node),
    type: node.type,
    color: NODE_TYPE_COLOR[node.type],
    size: nodeSizeFromDegree(degree),
    x: position.x,
    y: position.y,
  });
}

function addGraphEdge(graph: Graph, edge: OrgNetworkEdge): void {
  const solidarity = edge.mode === "solidarity";
  graph.addEdgeWithKey(`${edge.source}->${edge.target}#${edge.mode}`, edge.source, edge.target, {
    mode: edge.mode,
    solidarity,
    color: solidarity ? SOLIDARITY_EDGE_COLOR : DEFAULT_EDGE_COLOR,
    size: solidarity ? SOLIDARITY_EDGE_SIZE : DEFAULT_EDGE_SIZE,
  });
}

/**
 * Build a graphology `Graph` from an `OrgNetworkPayload` — one graph node
 * per payload node (sized by real degree centrality, colored by type,
 * positioned deterministically), one graph edge per payload edge (colored/
 * flagged distinctly for SOLIDARITY, defensively skipped if either endpoint
 * is missing from the payload's own node set).
 */
export function buildOrgNetworkGraph(payload: OrgNetworkPayload): Graph {
  const graph = new Graph({ type: "directed", multi: true });
  const positions = computeCircularLayout(payload.nodes.map((n) => n.id));

  for (const node of payload.nodes) {
    const degree = payload.centrality[node.id]?.degree ?? 0;
    const position = positions.get(node.id) ?? { x: 0, y: 0 };
    addGraphNode(graph, node, degree, position);
  }

  for (const edge of payload.edges) {
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;
    addGraphEdge(graph, edge);
  }

  return graph;
}
