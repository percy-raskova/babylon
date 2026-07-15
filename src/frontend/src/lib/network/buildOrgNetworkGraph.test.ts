/**
 * Tests for the org-network graph builder (AW4-R2) — pure payload -> graphology
 * `Graph` transform, no sigma/DOM involved. Covers: node count, size
 * monotonic in real (backend-supplied) degree centrality, node color by
 * type, SOLIDARITY-edge distinct styling, deterministic layout, and the
 * honest present-types/present-modes helpers the legend reads.
 */

import { describe, it, expect } from "vitest";
import {
  buildOrgNetworkGraph,
  computeCircularLayout,
  presentEdgeModes,
  presentNodeTypes,
  nodeSizeFromDegree,
  NODE_TYPE_COLOR,
  SOLIDARITY_EDGE_COLOR,
  DEFAULT_EDGE_COLOR,
} from "./buildOrgNetworkGraph";
import {
  makeOrgNetworkPayload,
  makeOrgNetworkNode,
  makeOrgNetworkEdge,
  makeOrgNetworkCentrality,
} from "@/test/fixtures";

describe("computeCircularLayout", () => {
  it("returns an empty map for zero ids", () => {
    expect(computeCircularLayout([]).size).toBe(0);
  });

  it("places every id at a distinct position", () => {
    const positions = computeCircularLayout(["a", "b", "c"]);
    expect(positions.size).toBe(3);
    const points = [...positions.values()];
    const unique = new Set(points.map((p) => `${p.x},${p.y}`));
    expect(unique.size).toBe(3);
  });

  it("is deterministic: same ids (any input order) yield the same positions", () => {
    const first = computeCircularLayout(["c", "a", "b"]);
    const second = computeCircularLayout(["a", "b", "c"]);
    expect(first.get("a")).toEqual(second.get("a"));
    expect(first.get("b")).toEqual(second.get("b"));
    expect(first.get("c")).toEqual(second.get("c"));
  });
});

describe("nodeSizeFromDegree", () => {
  it("is monotonic: a higher degree never yields a smaller size", () => {
    expect(nodeSizeFromDegree(0.9)).toBeGreaterThan(nodeSizeFromDegree(0.1));
    expect(nodeSizeFromDegree(0)).toBeLessThanOrEqual(nodeSizeFromDegree(1));
  });

  it("clamps to a sane pixel range for out-of-band input", () => {
    expect(nodeSizeFromDegree(-1)).toBe(nodeSizeFromDegree(0));
    expect(nodeSizeFromDegree(5)).toBe(nodeSizeFromDegree(1));
  });
});

describe("presentNodeTypes / presentEdgeModes", () => {
  it("returns an empty, honest list for an empty payload", () => {
    const payload = makeOrgNetworkPayload();
    expect(presentNodeTypes(payload)).toEqual([]);
    expect(presentEdgeModes(payload)).toEqual([]);
  });

  it("returns only the types/modes actually present, sorted, deduped", () => {
    const payload = makeOrgNetworkPayload({
      nodes: [
        makeOrgNetworkNode({ id: "org-1", type: "organization" }),
        makeOrgNetworkNode({ id: "org-2", type: "organization" }),
        makeOrgNetworkNode({ id: "terr-1", type: "territory" }),
      ],
      edges: [
        makeOrgNetworkEdge({ source: "org-1", target: "terr-1", mode: "presence" }),
        makeOrgNetworkEdge({ source: "org-2", target: "terr-1", mode: "presence" }),
      ],
    });
    expect(presentNodeTypes(payload)).toEqual(["organization", "territory"]);
    expect(presentEdgeModes(payload)).toEqual(["presence"]);
  });

  it("surfaces solidarity as its own present mode when it appears", () => {
    const payload = makeOrgNetworkPayload({
      nodes: [
        makeOrgNetworkNode({ id: "org-1", type: "organization" }),
        makeOrgNetworkNode({ id: "org-2", type: "organization" }),
      ],
      edges: [
        makeOrgNetworkEdge({ source: "org-1", target: "org-2", mode: "solidarity" }),
        makeOrgNetworkEdge({ source: "org-1", target: "org-2", mode: "houses" }),
      ],
    });
    expect(presentEdgeModes(payload)).toEqual(["houses", "solidarity"]);
  });
});

describe("buildOrgNetworkGraph", () => {
  const payload = makeOrgNetworkPayload({
    nodes: [
      makeOrgNetworkNode({ id: "org-1", type: "organization" }),
      makeOrgNetworkNode({ id: "inst-1", type: "institution" }),
      makeOrgNetworkNode({ id: "terr-1", type: "territory" }),
    ],
    edges: [
      makeOrgNetworkEdge({ source: "org-1", target: "terr-1", mode: "presence" }),
      makeOrgNetworkEdge({ source: "inst-1", target: "org-1", mode: "houses" }),
      makeOrgNetworkEdge({ source: "org-1", target: "inst-1", mode: "solidarity" }),
    ],
    centrality: {
      "org-1": makeOrgNetworkCentrality({ degree: 1.0 }),
      "inst-1": makeOrgNetworkCentrality({ degree: 0.5 }),
      "terr-1": makeOrgNetworkCentrality({ degree: 0.1 }),
    },
  });

  it("adds exactly one graph node per payload node", () => {
    const graph = buildOrgNetworkGraph(payload);
    expect(graph.order).toBe(3);
    expect(graph.hasNode("org-1")).toBe(true);
    expect(graph.hasNode("inst-1")).toBe(true);
    expect(graph.hasNode("terr-1")).toBe(true);
  });

  it("colors nodes by type using the real payload attributes types", () => {
    const graph = buildOrgNetworkGraph(payload);
    expect(graph.getNodeAttribute("org-1", "color")).toBe(NODE_TYPE_COLOR.organization);
    expect(graph.getNodeAttribute("inst-1", "color")).toBe(NODE_TYPE_COLOR.institution);
    expect(graph.getNodeAttribute("terr-1", "color")).toBe(NODE_TYPE_COLOR.territory);
  });

  it("sizes nodes monotonically in the backend's own degree centrality", () => {
    const graph = buildOrgNetworkGraph(payload);
    const sizeOrg1 = graph.getNodeAttribute("org-1", "size") as number; // degree 1.0
    const sizeInst1 = graph.getNodeAttribute("inst-1", "size") as number; // degree 0.5
    const sizeTerr1 = graph.getNodeAttribute("terr-1", "size") as number; // degree 0.1
    expect(sizeOrg1).toBeGreaterThan(sizeInst1);
    expect(sizeInst1).toBeGreaterThan(sizeTerr1);
  });

  it("falls back to zero degree when a node has no centrality entry (honest, never fabricated)", () => {
    const sparsePayload = makeOrgNetworkPayload({
      nodes: [makeOrgNetworkNode({ id: "org-orphan" })],
      centrality: {},
    });
    const graph = buildOrgNetworkGraph(sparsePayload);
    expect(graph.getNodeAttribute("org-orphan", "size")).toBe(nodeSizeFromDegree(0));
  });

  it("adds exactly one graph edge per payload edge", () => {
    const graph = buildOrgNetworkGraph(payload);
    expect(graph.size).toBe(3);
  });

  it("flags SOLIDARITY edges distinctly from every other mode", () => {
    const graph = buildOrgNetworkGraph(payload);
    const edges = graph.edges().map((e) => ({
      mode: graph.getEdgeAttribute(e, "mode") as string,
      solidarity: graph.getEdgeAttribute(e, "solidarity") as boolean,
      color: graph.getEdgeAttribute(e, "color") as string,
    }));

    const solidarityEdge = edges.find((e) => e.mode === "solidarity");
    const otherEdges = edges.filter((e) => e.mode !== "solidarity");

    expect(solidarityEdge?.solidarity).toBe(true);
    expect(solidarityEdge?.color).toBe(SOLIDARITY_EDGE_COLOR);
    expect(otherEdges.length).toBeGreaterThan(0);
    for (const e of otherEdges) {
      expect(e.solidarity).toBe(false);
      expect(e.color).toBe(DEFAULT_EDGE_COLOR);
    }
  });

  it("assigns each node a deterministic (x, y) — rebuilding the same payload yields identical positions", () => {
    const first = buildOrgNetworkGraph(payload);
    const second = buildOrgNetworkGraph(payload);
    for (const id of ["org-1", "inst-1", "terr-1"]) {
      expect(first.getNodeAttribute(id, "x")).toBe(second.getNodeAttribute(id, "x"));
      expect(first.getNodeAttribute(id, "y")).toBe(second.getNodeAttribute(id, "y"));
    }
  });

  it("is honestly empty for an empty payload — zero nodes, zero edges, no fabrication", () => {
    const graph = buildOrgNetworkGraph(makeOrgNetworkPayload());
    expect(graph.order).toBe(0);
    expect(graph.size).toBe(0);
  });

  it("skips an edge referencing a node outside the payload's own node set (defensive honesty)", () => {
    const malformed = makeOrgNetworkPayload({
      nodes: [makeOrgNetworkNode({ id: "org-1" })],
      edges: [makeOrgNetworkEdge({ source: "org-1", target: "ghost-node" })],
    });
    const graph = buildOrgNetworkGraph(malformed);
    expect(graph.order).toBe(1);
    expect(graph.size).toBe(0);
  });
});
