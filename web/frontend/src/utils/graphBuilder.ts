/**
 * Build a Graphology graph from a GameSnapshot.
 *
 * Converts organizations, institutions, territories, and edges into
 * graph nodes and edges for Sigma.js visualization.
 *
 * Note: Entity nodes are NOT rendered — classes are derived aggregations,
 * not graph-level agents (Spec 052 §3, invariant 1).
 */

import Graph from "graphology";
import type { GameSnapshot } from "@/types/game";

/** Node attributes stored in the Graphology graph. */
export interface NodeAttrs {
  label: string;
  x: number;
  y: number;
  size: number;
  color: string;
  nodeType: "territory" | "organization" | "institution";
}

/** Edge attributes stored in the Graphology graph. */
export interface EdgeAttrs {
  label: string;
  color: string;
  size: number;
  edgeType: string;
}

// Deterministic initial positions from a hash of the node ID.
function hashPosition(id: string, seed: number): number {
  let h = seed;
  for (let i = 0; i < id.length; i++) {
    h = (h * 31 + id.charCodeAt(i)) | 0;
  }
  return ((h % 1000) / 1000) * 2 - 1; // [-1, 1]
}

const NODE_COLORS: Record<NodeAttrs["nodeType"], string> = {
  territory: "#d4a843", // gold
  organization: "#9b59b6", // grow-purple
  institution: "#b0b0c0", // silver
};

const EDGE_COLORS: Record<string, string> = {
  EXTRACTIVE: "#e63946", // crimson
  TRANSACTIONAL: "#4ade80", // data-green
  SOLIDARISTIC: "#d4a843", // gold
  ANTAGONISTIC: "#ff6b35", // orange-red
  CO_OPTIVE: "#9b59b6", // purple
};

/**
 * Build a Graphology graph from a snapshot.
 *
 * @param snapshot - The current game state snapshot.
 * @returns A new Graphology graph with nodes and edges.
 */
export function buildGraph(snapshot: GameSnapshot): Graph<NodeAttrs, EdgeAttrs> {
  const graph = new Graph<NodeAttrs, EdgeAttrs>({ multi: true, type: "directed" });

  // Add territory nodes
  for (const t of snapshot.territories) {
    if (!graph.hasNode(t.id)) {
      graph.addNode(t.id, {
        label: t.name,
        x: hashPosition(t.id, 3) * 100,
        y: hashPosition(t.id, 4) * 100,
        size: 3 + Math.min(t.heat * 8, 10),
        color: NODE_COLORS.territory,
        nodeType: "territory",
      });
    }
  }

  // Add organization nodes
  for (const o of snapshot.organizations) {
    if (!graph.hasNode(o.id)) {
      graph.addNode(o.id, {
        label: o.name,
        x: hashPosition(o.id, 5) * 100,
        y: hashPosition(o.id, 6) * 100,
        size: 5 + Math.min(o.budget / 5, 10),
        color: NODE_COLORS.organization,
        nodeType: "organization",
      });
    }
  }

  // Add institution nodes
  for (const inst of snapshot.institutions) {
    if (!graph.hasNode(inst.id)) {
      graph.addNode(inst.id, {
        label: inst.name,
        x: hashPosition(inst.id, 7) * 100,
        y: hashPosition(inst.id, 8) * 100,
        size: 6,
        color: NODE_COLORS.institution,
        nodeType: "institution",
      });
    }
  }

  // Add edges
  for (const edge of snapshot.edges) {
    if (!graph.hasNode(edge.source_id) || !graph.hasNode(edge.target_id)) continue;
    const edgeColor = EDGE_COLORS[edge.mode] ?? "#3a3a4a";
    graph.addEdge(edge.source_id, edge.target_id, {
      label: edge.mode,
      color: edgeColor,
      size: 0.5 + Math.min(Math.abs(edge.value_flow) / 10, 2),
      edgeType: edge.mode,
    });
  }

  return graph;
}
