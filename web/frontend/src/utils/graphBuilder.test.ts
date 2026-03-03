/**
 * Unit tests for the Graphology graph builder.
 */

import { describe, it, expect } from "vitest";
import { buildGraph } from "./graphBuilder";
import { makeSnapshot, makeEdge } from "@/test/fixtures";

describe("buildGraph", () => {
  it("creates entity nodes", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    expect(graph.hasNode("entity-proletariat")).toBe(true);
    expect(graph.hasNode("entity-bourgeoisie")).toBe(true);
    expect(graph.getNodeAttribute("entity-proletariat", "nodeType")).toBe("entity");
    expect(graph.getNodeAttribute("entity-proletariat", "label")).toBe("Proletariat");
  });

  it("creates territory nodes", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    expect(graph.hasNode("territory-downtown")).toBe(true);
    expect(graph.getNodeAttribute("territory-downtown", "nodeType")).toBe("territory");
    expect(graph.getNodeAttribute("territory-downtown", "label")).toBe("Downtown");
  });

  it("creates organization nodes", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    expect(graph.hasNode("org-workers-union")).toBe(true);
    expect(graph.getNodeAttribute("org-workers-union", "nodeType")).toBe("organization");
  });

  it("creates institution nodes", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    expect(graph.hasNode("inst-city-hall")).toBe(true);
    expect(graph.getNodeAttribute("inst-city-hall", "nodeType")).toBe("institution");
  });

  it("creates edges between existing nodes", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    // EXPLOITATION edge: proletariat -> bourgeoisie
    const edges = graph.edges("entity-proletariat", "entity-bourgeoisie");
    expect(edges.length).toBeGreaterThan(0);
    const firstEdge = edges[0];
    expect(firstEdge).toBeDefined();
    if (!firstEdge) {
      throw new Error("Expected at least one edge");
    }
    const edgeAttrs = graph.getEdgeAttributes(firstEdge);
    expect(edgeAttrs.edgeType).toBe("EXPLOITATION");
  });

  it("skips edges with missing nodes", () => {
    const snap = makeSnapshot({
      edges: [makeEdge({ source_id: "nonexistent", target_id: "entity-proletariat" })],
    });
    const graph = buildGraph(snap);

    expect(graph.size).toBe(0); // No edges
  });

  it("handles empty snapshot", () => {
    const snap = makeSnapshot({
      entities: [],
      territories: [],
      organizations: [],
      institutions: [],
      edges: [],
      events: [],
    });
    const graph = buildGraph(snap);

    expect(graph.order).toBe(0);
    expect(graph.size).toBe(0);
  });

  it("assigns node positions", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    const x = graph.getNodeAttribute("entity-proletariat", "x");
    const y = graph.getNodeAttribute("entity-proletariat", "y");
    expect(typeof x).toBe("number");
    expect(typeof y).toBe("number");
  });

  it("assigns node sizes based on data", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    const proletariatSize = graph.getNodeAttribute("entity-proletariat", "size");
    const bourgeoisieSize = graph.getNodeAttribute("entity-bourgeoisie", "size");
    // Bourgeoisie has wealth 200, proletariat 25 -> different sizes
    expect(bourgeoisieSize).toBeGreaterThan(proletariatSize);
  });

  it("assigns correct node colors by type", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    expect(graph.getNodeAttribute("entity-proletariat", "color")).toBe("#6a9fdb");
    expect(graph.getNodeAttribute("territory-downtown", "color")).toBe("#d4a843");
    expect(graph.getNodeAttribute("org-workers-union", "color")).toBe("#9b59b6");
    expect(graph.getNodeAttribute("inst-city-hall", "color")).toBe("#b0b0c0");
  });

  it("assigns edge colors by type", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    const exploitEdges = graph.edges("entity-proletariat", "entity-bourgeoisie");
    const firstExploitEdge = exploitEdges[0];
    expect(firstExploitEdge).toBeDefined();
    if (!firstExploitEdge) {
      throw new Error("Expected exploitation edge");
    }
    const edgeColor = graph.getEdgeAttribute(firstExploitEdge, "color");
    expect(edgeColor).toBe("#e63946"); // EXPLOITATION -> crimson
  });
});
