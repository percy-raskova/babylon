/**
 * Unit tests for the Graphology graph builder (Spec 052).
 *
 * Note: Entity nodes are NOT rendered — classes are derived aggregations.
 * The graph contains only organizations, institutions, and territories.
 */

import { describe, it, expect } from "vitest";
import { buildGraph } from "./graphBuilder";
import {
  makeSnapshot,
  makeEdge,
  makeOrg,
  makeInstitution,
  makeTerritory,
  makeConsciousness,
  makeOoda,
  makeFactionalComposition,
} from "@/test/fixtures";

describe("buildGraph", () => {
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

  it("does NOT create entity nodes (Spec 052 invariant 1)", () => {
    // Entities are derived aggregations, not graph nodes
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    // No node should have nodeType "entity"
    graph.forEachNode((_node, attrs) => {
      expect(attrs.nodeType).not.toBe("entity");
    });
  });

  it("creates edges between existing nodes", () => {
    const snap = makeSnapshot({
      edges: [
        makeEdge({
          id: "edge-01",
          source_id: "org-workers-union",
          target_id: "territory-downtown",
          mode: "SOLIDARISTIC",
        }),
      ],
    });
    const graph = buildGraph(snap);

    const edges = graph.edges("org-workers-union", "territory-downtown");
    expect(edges.length).toBeGreaterThan(0);
    const firstEdge = edges[0];
    expect(firstEdge).toBeDefined();
    if (!firstEdge) {
      throw new Error("Expected at least one edge");
    }
    const edgeAttrs = graph.getEdgeAttributes(firstEdge);
    expect(edgeAttrs.edgeType).toBe("SOLIDARISTIC");
  });

  it("skips edges with missing nodes", () => {
    const snap = makeSnapshot({
      edges: [makeEdge({ source_id: "nonexistent", target_id: "org-workers-union" })],
    });
    const graph = buildGraph(snap);

    expect(graph.size).toBe(0); // No edges
  });

  it("handles empty snapshot", () => {
    const snap = makeSnapshot({
      territories: [],
      organizations: [],
      institutions: [],
      edges: [],
      events: [],
      hyperedges: [],
    });
    const graph = buildGraph(snap);

    expect(graph.order).toBe(0);
    expect(graph.size).toBe(0);
  });

  it("assigns node positions", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    const x = graph.getNodeAttribute("org-workers-union", "x");
    const y = graph.getNodeAttribute("org-workers-union", "y");
    expect(typeof x).toBe("number");
    expect(typeof y).toBe("number");
  });

  it("assigns correct node colors by type", () => {
    const snap = makeSnapshot();
    const graph = buildGraph(snap);

    expect(graph.getNodeAttribute("territory-downtown", "color")).toBe("#d4a843");
    expect(graph.getNodeAttribute("org-workers-union", "color")).toBe("#9b59b6");
    expect(graph.getNodeAttribute("inst-city-hall", "color")).toBe("#b0b0c0");
  });

  it("assigns edge colors by mode", () => {
    const snap = makeSnapshot({
      edges: [
        makeEdge({
          id: "edge-ext",
          source_id: "org-workers-union",
          target_id: "territory-downtown",
          mode: "EXTRACTIVE",
        }),
      ],
    });
    const graph = buildGraph(snap);

    const edges = graph.edges("org-workers-union", "territory-downtown");
    const firstEdge = edges[0];
    expect(firstEdge).toBeDefined();
    if (!firstEdge) throw new Error("Expected edge");
    const edgeColor = graph.getEdgeAttribute(firstEdge, "color");
    expect(edgeColor).toBe("#e63946"); // EXTRACTIVE → crimson
  });

  it("handles duplicate IDs across territory and org without throwing", () => {
    const snap = makeSnapshot({
      territories: [makeTerritory({ id: "shared-id", name: "Downtown" })],
      organizations: [makeOrg({ id: "shared-id", name: "OrgSameId" })],
      institutions: [],
      edges: [],
    });
    // Should NOT throw even if IDs collide — hasNode guard
    expect(() => buildGraph(snap)).not.toThrow();
  });

  it("handles duplicate IDs across org and institution without throwing", () => {
    const snap = makeSnapshot({
      territories: [],
      organizations: [makeOrg({ id: "dup-id", name: "Org" })],
      institutions: [makeInstitution({ id: "dup-id", name: "Inst" })],
      edges: [],
    });
    expect(() => buildGraph(snap)).not.toThrow();
  });

  it("builds graph from a realistic Wayne County snapshot", () => {
    const snap = makeSnapshot({
      territories: [
        makeTerritory({ id: "terr-wayne-01", name: "Wayne Central" }),
        makeTerritory({ id: "terr-wayne-02", name: "Wayne Industrial" }),
        makeTerritory({ id: "terr-oakland-01", name: "Oakland Suburbs" }),
      ],
      organizations: [
        makeOrg({
          id: "org-peoples-front",
          name: "People's United Front",
          org_type: "civil_society_org",
          class_character: "proletarian",
          consciousness: makeConsciousness({ revolutionary: 0.8, liberal: 0.15, fascist: 0.05 }),
          ooda: makeOoda(),
        }),
        makeOrg({
          id: "org-state-apparatus",
          name: "Michigan State Apparatus",
          org_type: "state_apparatus",
          class_character: "bourgeois",
          consciousness: makeConsciousness({ revolutionary: 0.01, liberal: 0.49, fascist: 0.5 }),
          ooda: makeOoda(),
        }),
        makeOrg({
          id: "org-auto-union",
          name: "Auto Workers Union",
          org_type: "civil_society_org",
          class_character: "proletarian",
          consciousness: makeConsciousness({ revolutionary: 0.4, liberal: 0.5, fascist: 0.1 }),
          ooda: makeOoda(),
        }),
        makeOrg({
          id: "org-proud-boys",
          name: "Proud Boys",
          org_type: "political_faction",
          class_character: "settler",
          consciousness: makeConsciousness({ revolutionary: 0.0, liberal: 0.1, fascist: 0.9 }),
          ooda: makeOoda(),
        }),
      ],
      institutions: [
        makeInstitution({
          id: "inst-city-hall",
          name: "City Hall",
          factional_composition: makeFactionalComposition(),
        }),
        makeInstitution({
          id: "inst-police-hq",
          name: "Police Headquarters",
          factional_composition: makeFactionalComposition({
            revanchist_fascist: 0.6,
            liberal_technocratic: 0.2,
            institutionalist_bonapartist: 0.2,
          }),
        }),
      ],
      edges: [
        makeEdge({
          id: "e1",
          source_id: "org-peoples-front",
          target_id: "org-auto-union",
          mode: "SOLIDARISTIC",
        }),
        makeEdge({
          id: "e2",
          source_id: "org-state-apparatus",
          target_id: "org-peoples-front",
          mode: "EXTRACTIVE",
        }),
        makeEdge({
          id: "e3",
          source_id: "org-proud-boys",
          target_id: "org-peoples-front",
          mode: "ANTAGONISTIC",
        }),
        makeEdge({
          id: "e4",
          source_id: "terr-wayne-01",
          target_id: "terr-wayne-02",
          mode: "TRANSACTIONAL",
        }),
        makeEdge({
          id: "e5",
          source_id: "terr-wayne-02",
          target_id: "terr-oakland-01",
          mode: "TRANSACTIONAL",
        }),
        makeEdge({
          id: "e6",
          source_id: "inst-city-hall",
          target_id: "org-state-apparatus",
          mode: "CO_OPTIVE",
        }),
      ],
    });

    expect(() => buildGraph(snap)).not.toThrow();
    const graph = buildGraph(snap);

    // 3 territories + 4 orgs + 2 institutions = 9 nodes
    expect(graph.order).toBe(9);
    // 6 edges all have valid endpoints
    expect(graph.size).toBe(6);
  });
});
