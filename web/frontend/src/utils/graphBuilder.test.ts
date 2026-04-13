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

  // -- RED-PHASE: crash resilience for mock bridge data --

  it("handles duplicate IDs across entity and territory without throwing", () => {
    // If MockEngineBridge produces an entity and territory with the same ID,
    // graphology.addNode throws "already exists". The builder must guard
    // against this by checking hasNode() first.
    const snap = makeSnapshot({
      entities: [
        {
          id: "shared-id",
          name: "Worker",
          role: "proletariat",
          wealth: 25,
          consciousness: 0.3,
          national_identity: 0.5,
          agitation: 0.2,
          organization: 0.15,
          repression: 0.4,
          p_acquiescence: 0.7,
          p_revolution: 0.1,
          subsistence: 10,
          population: 50000,
          inequality: 0.45,
          active: true,
        },
      ],
      territories: [
        {
          id: "shared-id",
          name: "Downtown",
          h3_index: "882a100d2bfffff",
          heat: 0.4,
          sector_type: "INDUSTRIAL",
          territory_type: "URBAN",
          profile: "HIGH_PROFILE",
          rent_level: 0.6,
          population: 12000,
          under_eviction: false,
          biocapacity: 0.3,
          host_id: null,
          occupant_id: null,
        },
      ],
      organizations: [],
      institutions: [],
      edges: [],
    });
    // This should NOT throw even if IDs collide
    expect(() => buildGraph(snap)).not.toThrow();
  });

  it("handles duplicate IDs across org and institution without throwing", () => {
    const snap = makeSnapshot({
      entities: [],
      territories: [],
      organizations: [
        {
          id: "dup-id",
          name: "Org",
          org_type: "civil_society",
          class_character: "proletarian",
          cohesion: 0.5,
          cadre_level: 1,
          budget: 10,
          heat: 0,
          territory_ids: [],
          consciousness_tendency: "revolutionary",
        },
      ],
      institutions: [
        {
          id: "dup-id",
          name: "Inst",
          apparatus_type: "RSA",
          social_function: "governance",
          class_inscription: "bourgeoisie",
          legitimacy: 0.6,
          budget: 50,
          housed_org_ids: [],
          territory_ids: [],
          hegemonic_fraction: "liberal_technocratic",
          liberal_technocratic: 0.5,
          revanchist_fascist: 0.2,
          institutionalist_bonapartist: 0.3,
        },
      ],
      edges: [],
    });
    expect(() => buildGraph(snap)).not.toThrow();
  });

  it("builds the exact mock bridge snapshot shape (10 nodes, 11 edges)", () => {
    // Reproduce the IDs from MockEngineBridge._build_initial_snapshot
    const snap = makeSnapshot({
      entities: [
        {
          id: "ent-proletariat",
          name: "Detroit Proletariat",
          role: "proletariat",
          wealth: 20,
          consciousness: 0.1,
          national_identity: 0.2,
          agitation: 0.2,
          organization: 0.1,
          repression: 0.5,
          p_acquiescence: 0.75,
          p_revolution: 0.05,
          subsistence: 10,
          population: 640000,
          inequality: 0.55,
          active: true,
        },
        {
          id: "ent-bourgeoisie",
          name: "Wayne County Bourgeoisie",
          role: "core_bourgeoisie",
          wealth: 200,
          consciousness: 0.01,
          national_identity: 0.8,
          agitation: 0.05,
          organization: 0.8,
          repression: 0.05,
          p_acquiescence: 0.95,
          p_revolution: 0.01,
          subsistence: 50,
          population: 50000,
          inequality: 0.2,
          active: true,
        },
        {
          id: "ent-labor-aristocracy",
          name: "Suburban Labor Aristocracy",
          role: "labor_aristocracy",
          wealth: 80,
          consciousness: 0.05,
          national_identity: 0.6,
          agitation: 0.1,
          organization: 0.3,
          repression: 0.1,
          p_acquiescence: 0.9,
          p_revolution: 0.02,
          subsistence: 30,
          population: 800000,
          inequality: 0.3,
          active: true,
        },
        {
          id: "ent-lumpen",
          name: "Lumpenproletariat",
          role: "lumpenproletariat",
          wealth: 5,
          consciousness: 0.02,
          national_identity: 0.1,
          agitation: 0.4,
          organization: 0.02,
          repression: 0.85,
          p_acquiescence: 0.6,
          p_revolution: 0.08,
          subsistence: 5,
          population: 120000,
          inequality: 0.8,
          active: true,
        },
      ],
      territories: [
        {
          id: "terr-wayne-01",
          name: "Wayne Central",
          h3_index: "8428309daffffff",
          heat: 0.3,
          sector_type: "INDUSTRIAL",
          territory_type: "URBAN",
          profile: "HIGH_PROFILE",
          rent_level: 0.6,
          population: 200000,
          under_eviction: false,
          biocapacity: 0.3,
          host_id: null,
          occupant_id: null,
        },
        {
          id: "terr-wayne-02",
          name: "Wayne Industrial",
          h3_index: "84283091fffffff",
          heat: 0.2,
          sector_type: "INDUSTRIAL",
          territory_type: "URBAN",
          profile: "LOW_PROFILE",
          rent_level: 0.4,
          population: 150000,
          under_eviction: false,
          biocapacity: 0.4,
          host_id: null,
          occupant_id: null,
        },
        {
          id: "terr-oakland-01",
          name: "Oakland Suburbs",
          h3_index: "84283097fffffff",
          heat: 0.05,
          sector_type: "RESIDENTIAL",
          territory_type: "SUBURBAN",
          profile: "LOW_PROFILE",
          rent_level: 0.8,
          population: 300000,
          under_eviction: false,
          biocapacity: 0.6,
          host_id: null,
          occupant_id: null,
        },
      ],
      organizations: [
        {
          id: "org-peoples-front",
          name: "People's United Front",
          org_type: "civil_society",
          class_character: "proletarian",
          cohesion: 0.6,
          cadre_level: 1,
          budget: 12,
          heat: 0.2,
          territory_ids: ["terr-wayne-01"],
          consciousness_tendency: "revolutionary",
        },
        {
          id: "org-state-apparatus",
          name: "Michigan State Apparatus",
          org_type: "STATE_APPARATUS",
          class_character: "bourgeois",
          cohesion: 0.8,
          cadre_level: 5,
          budget: 200,
          heat: 0,
          territory_ids: [],
          consciousness_tendency: "reactionary",
        },
        {
          id: "org-auto-union",
          name: "Auto Workers Union",
          org_type: "civil_society",
          class_character: "proletarian",
          cohesion: 0.5,
          cadre_level: 0,
          budget: 8,
          heat: 0.1,
          territory_ids: [],
          consciousness_tendency: "reformist",
        },
        {
          id: "org-militia",
          name: "Settler Reactionary Militia",
          org_type: "PARAMILITARY",
          class_character: "settler",
          cohesion: 0.7,
          cadre_level: 3,
          budget: 15,
          heat: 0.4,
          territory_ids: ["terr-oakland-01"],
          consciousness_tendency: "fascist",
        },
      ],
      institutions: [
        {
          id: "inst-city-hall",
          name: "City Hall",
          apparatus_type: "RSA",
          social_function: "governance",
          class_inscription: "bourgeoisie",
          legitimacy: 0.7,
          budget: 100,
          housed_org_ids: ["org-state-apparatus"],
          territory_ids: ["terr-wayne-01"],
          hegemonic_fraction: "liberal_technocratic",
          liberal_technocratic: 0.5,
          revanchist_fascist: 0.2,
          institutionalist_bonapartist: 0.3,
        },
        {
          id: "inst-police-hq",
          name: "Police Headquarters",
          apparatus_type: "ISA",
          social_function: "repression",
          class_inscription: "bourgeoisie",
          legitimacy: 0.5,
          budget: 80,
          housed_org_ids: [],
          territory_ids: ["terr-wayne-01"],
          hegemonic_fraction: "revanchist_fascist",
          liberal_technocratic: 0.2,
          revanchist_fascist: 0.6,
          institutionalist_bonapartist: 0.2,
        },
      ],
      edges: [
        {
          source_id: "ent-bourgeoisie",
          target_id: "ent-proletariat",
          edge_type: "EXPLOITATION",
          value_flow: 15,
          tension: 0.5,
          solidarity_strength: 0,
        },
        {
          source_id: "ent-bourgeoisie",
          target_id: "ent-labor-aristocracy",
          edge_type: "WAGES",
          value_flow: 5,
          tension: 0.1,
          solidarity_strength: 0,
        },
        {
          source_id: "ent-bourgeoisie",
          target_id: "ent-lumpen",
          edge_type: "EXPLOITATION",
          value_flow: 8,
          tension: 0.7,
          solidarity_strength: 0,
        },
        {
          source_id: "ent-proletariat",
          target_id: "org-peoples-front",
          edge_type: "SOLIDARITY",
          value_flow: 0,
          tension: 0,
          solidarity_strength: 0.4,
        },
        {
          source_id: "org-peoples-front",
          target_id: "terr-wayne-01",
          edge_type: "HOUSES",
          value_flow: 0,
          tension: 0,
          solidarity_strength: 0,
        },
        {
          source_id: "org-auto-union",
          target_id: "ent-proletariat",
          edge_type: "SOLIDARITY",
          value_flow: 0,
          tension: 0,
          solidarity_strength: 0.3,
        },
        {
          source_id: "org-state-apparatus",
          target_id: "ent-proletariat",
          edge_type: "EXPLOITATION",
          value_flow: 10,
          tension: 0.6,
          solidarity_strength: 0,
        },
        {
          source_id: "terr-wayne-01",
          target_id: "terr-wayne-02",
          edge_type: "ADJACENCY",
          value_flow: 0,
          tension: 0,
          solidarity_strength: 0,
        },
        {
          source_id: "terr-wayne-02",
          target_id: "terr-oakland-01",
          edge_type: "ADJACENCY",
          value_flow: 0,
          tension: 0,
          solidarity_strength: 0,
        },
        {
          source_id: "terr-oakland-01",
          target_id: "terr-wayne-01",
          edge_type: "ADJACENCY",
          value_flow: 0,
          tension: 0,
          solidarity_strength: 0,
        },
        {
          source_id: "inst-city-hall",
          target_id: "ent-bourgeoisie",
          edge_type: "HOUSES",
          value_flow: 0,
          tension: 0,
          solidarity_strength: 0,
        },
      ],
    });

    expect(() => buildGraph(snap)).not.toThrow();
    const graph = buildGraph(snap);

    // 4 entities + 3 territories + 4 orgs + 2 institutions = 13
    expect(graph.order).toBe(13);
    // 11 edges all have valid endpoints
    expect(graph.size).toBe(11);
  });
});
