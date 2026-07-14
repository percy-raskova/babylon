import { describe, it, expect } from "vitest";
import { adaptNode } from "./node";

describe("adaptNode (social_class, Program 17 Wave 1 / W1.4+W1.6)", () => {
  const baseData = {
    type: "social_class",
    id: "C002",
    name: "Suburban Petty Bourgeoisie",
    role: "labor_aristocracy",
    wealth: 0.65,
    core_wages: 1.0,
    imperial_rent_gap: 0.35,
    unearned_increment: 0.0,
    ppp_multiplier: 1.0,
    effective_wealth: 0.0,
    population: 800000,
    organization: 0.3,
    repression_faced: 0.1,
    subsistence_threshold: 0.15,
    class_consciousness: 0.3,
    national_identity: 0.7,
    agitation: 0.0,
    inequality: 0.0,
    class_position: "Not yet modeled — placeholder for a future class-position taxonomy.",
    class_position_mock: true,
    consciousness: { revolutionary: 0.09, liberal: 0.42, fascist: 0.49 },
    apologist_claim: "The wage gap reflects a 'skill premium'.",
    apologist_refutation: "Core wages (1.0000) exceed value produced (0.6500) by 0.3500.",
  };

  it("titles from the node's real name", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, baseData);
    expect(node.title).toBe("Suburban Petty Bourgeoisie");
  });

  it("renders the wage-pairing fields in the main section", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, baseData);
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Role")?.value).toBe("labor_aristocracy");
    expect(rows.find((r) => r.label === "Wealth")?.value).toBe(0.65);
    expect(rows.find((r) => r.label === "Core Wages")?.value).toBe(1.0);
    expect(rows.find((r) => r.label === "Imperial Rent Gap")?.value).toBe(0.35);
    expect(rows.find((r) => r.label === "Population")?.value).toBe(800000);
  });

  it("renders Inequality as a real (non-mock) row", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, baseData);
    const row = node.sections[0]?.rows.find((r) => r.label === "Inequality");
    expect(row?.value).toBe(0.0);
    expect(row?.mock).toBeFalsy();
  });

  it("renders Class Position as a clearly-badged mock row", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, baseData);
    const row = node.sections[0]?.rows.find((r) => r.label === "Class Position");
    expect(row?.mock).toBe(true);
    expect(row?.value).toBe(baseData.class_position);
  });

  it("renders the ternary consciousness as a composition row", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, baseData);
    const ideologySection = node.sections.find((s) => s.label === "Ideology");
    const row = ideologySection?.rows.find((r) => r.label === "Consciousness");
    expect(row?.composition).toEqual([
      { key: "Revolutionary", value: 0.09, color: "text-laser" },
      { key: "Liberal", value: 0.42, color: "text-cadre" },
      { key: "Fascist", value: 0.49, color: "text-rupture" },
    ]);
  });

  it("renders Consciousness with an undefined composition when the backend sent no ternary", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, { ...baseData, consciousness: null });
    const ideologySection = node.sections.find((s) => s.label === "Ideology");
    const row = ideologySection?.rows.find((r) => r.label === "Consciousness");
    expect(row?.composition).toBeUndefined();
    expect(row?.value).toBeNull();
  });

  it("renders Agitation in the Ideology section", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, baseData);
    const ideologySection = node.sections.find((s) => s.label === "Ideology");
    expect(ideologySection?.rows.find((r) => r.label === "Agitation")?.value).toBe(0.0);
  });

  it("renders the apologist claim/refutation as its own section", () => {
    const node = adaptNode({ kind: "node", id: "C002" }, baseData);
    const section = node.sections.find((s) => s.label === "Imperial Apologetics");
    expect(section?.rows.find((r) => r.label === "Apologist Claim")?.value).toBe(
      baseData.apologist_claim,
    );
    expect(section?.rows.find((r) => r.label === "Apologist Refutation")?.value).toBe(
      baseData.apologist_refutation,
    );
  });

  describe("Imperial Circuit section (W1.6)", () => {
    const circuitFlows = {
      nodes: [
        { role: "core_bourgeoisie", id: "C003", name: "Wayne County Bourgeoisie" },
        { role: "labor_aristocracy", id: "C002", name: "Suburban Petty Bourgeoisie" },
      ],
      links: [
        {
          source_role: "core_bourgeoisie",
          target_role: "labor_aristocracy",
          source_id: "C003",
          target_id: "C002",
          value_flow: 1.0,
        },
      ],
    };

    it("attaches an Imperial Circuit section when circuit_flows is present and non-empty", () => {
      const node = adaptNode(
        { kind: "node", id: "C002" },
        { ...baseData, circuit_flows: circuitFlows },
      );
      const section = node.sections.find((s) => s.label === "Imperial Circuit");
      expect(section).toBeDefined();
      expect(section?.rows[0]?.circuitFlows).toEqual(circuitFlows);
    });

    it("omits the Imperial Circuit section when circuit_flows is absent", () => {
      const node = adaptNode({ kind: "node", id: "C002" }, baseData);
      expect(node.sections.find((s) => s.label === "Imperial Circuit")).toBeUndefined();
    });

    it("omits the Imperial Circuit section when circuit_flows carries no nodes", () => {
      const node = adaptNode(
        { kind: "node", id: "C002" },
        { ...baseData, circuit_flows: { nodes: [], links: [] } },
      );
      expect(node.sections.find((s) => s.label === "Imperial Circuit")).toBeUndefined();
    });
  });

  it("falls back to the generic entity dump for a non-social_class node (regression)", () => {
    const node = adaptNode({ kind: "node", id: "n1" }, { type: "node", details: "Stub details." });
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "type")?.value).toBe("node");
    expect(rows.find((r) => r.label === "details")?.value).toBe("Stub details.");
  });
});
