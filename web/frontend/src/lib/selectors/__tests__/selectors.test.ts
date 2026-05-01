/**
 * Selector registry, primitives, and derived selector tests.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { SelectorRegistry, selectors, GAMEDEFINES } from "@/lib/selectors";
import type { Scope, ScopeEntity } from "@/lib/selectors";
import { makeWayneCountySnapshot } from "@/test/fixtures";
import type { GameSnapshot } from "@/types/game";

let snap: GameSnapshot;

beforeEach(() => {
  snap = makeWayneCountySnapshot();
});

function makeScope(entity: ScopeEntity | null = null): Scope {
  return { snapshot: snap, this: entity };
}

// -----------------------------------------------------------------------
// Registry mechanics
// -----------------------------------------------------------------------

describe("SelectorRegistry", () => {
  it("throws on duplicate registration", () => {
    const reg = new SelectorRegistry();
    const sv = {
      name: "test.dup",
      label: "Dup",
      description: "",
      scopeKind: "hex" as const,
      evaluate: () => 0,
      breakdown: () => ({ total: 0, contributors: [] }),
    };
    reg.register(sv);
    expect(() => reg.register(sv)).toThrow('Selector "test.dup" is already registered.');
  });

  it("throws on unknown get", () => {
    const reg = new SelectorRegistry();
    expect(() => reg.get("nope")).toThrow('Selector "nope" is not registered.');
  });

  it("dump returns sorted names", () => {
    const reg = new SelectorRegistry();
    reg.register({
      name: "z.last",
      label: "",
      description: "",
      scopeKind: "hex" as const,
      evaluate: () => 0,
      breakdown: () => ({ total: 0, contributors: [] }),
    });
    reg.register({
      name: "a.first",
      label: "",
      description: "",
      scopeKind: "hex" as const,
      evaluate: () => 0,
      breakdown: () => ({ total: 0, contributors: [] }),
    });
    expect(reg.dump()).toEqual(["a.first", "z.last"]);
  });
});

// -----------------------------------------------------------------------
// Auto-registration — importing the barrel populates the global registry
// -----------------------------------------------------------------------

describe("Global registry auto-population", () => {
  it("has at least 6 primitives + 3 derived selectors", () => {
    expect(selectors.size).toBeGreaterThanOrEqual(9);
  });

  it("contains all expected selector names", () => {
    const names = selectors.dump();
    expect(names).toContain("hex.heat");
    expect(names).toContain("hex.rent_level");
    expect(names).toContain("hex.population");
    expect(names).toContain("hex.biocapacity");
    expect(names).toContain("org.cadre");
    expect(names).toContain("org.budget");
    expect(names).toContain("hex.imperial_rent");
    expect(names).toContain("org.effective_cadre");
    expect(names).toContain("org.consciousness_gap");
  });
});

// -----------------------------------------------------------------------
// Primitive selectors
// -----------------------------------------------------------------------

describe("Primitive selectors", () => {
  it("hex.heat reads territory heat", () => {
    const territory = snap.territories[0]!;
    territory.heat = 0.75;
    const sv = selectors.get("hex.heat");
    const scope = makeScope({ kind: "hex", id: territory.id });

    expect(sv.evaluate(scope)).toBe(0.75);

    const bd = sv.breakdown(scope);
    expect(bd.total).toBe(0.75);
    expect(bd.contributors).toHaveLength(1);
    expect(bd.contributors[0]!.source.kind).toBe("snapshot_field");
    expect(bd.contributors[0]!.source.path).toContain("heat");
  });

  it("hex.heat returns 0 for non-hex scope", () => {
    const sv = selectors.get("hex.heat");
    expect(sv.evaluate(makeScope(null))).toBe(0);
    expect(sv.evaluate(makeScope({ kind: "org", id: "org-1" }))).toBe(0);
  });

  it("hex.rent_level reads territory rent_level", () => {
    const territory = snap.territories[0]!;
    territory.rent_level = 0.42;
    const sv = selectors.get("hex.rent_level");
    expect(sv.evaluate(makeScope({ kind: "hex", id: territory.id }))).toBe(0.42);
  });

  it("hex.population reads territory population", () => {
    const territory = snap.territories[0]!;
    territory.population = 15000;
    const sv = selectors.get("hex.population");
    expect(sv.evaluate(makeScope({ kind: "hex", id: territory.id }))).toBe(15000);
  });

  it("org.cadre reads cadre_level", () => {
    const org = snap.organizations[0]!;
    org.cadre_level = 0.55;
    const sv = selectors.get("org.cadre");
    expect(sv.evaluate(makeScope({ kind: "org", id: org.id }))).toBe(0.55);
  });

  it("org.budget reads budget", () => {
    const org = snap.organizations[0]!;
    org.budget = 500;
    const sv = selectors.get("org.budget");
    expect(sv.evaluate(makeScope({ kind: "org", id: org.id }))).toBe(500);
  });
});

// -----------------------------------------------------------------------
// Derived selectors
// -----------------------------------------------------------------------

describe("Derived selectors", () => {
  it("org.effective_cadre applies heat penalty", () => {
    const org = snap.organizations[0]!;
    org.cadre_level = 1.0;
    org.heat = 0.5;
    const sv = selectors.get("org.effective_cadre");
    const scope = makeScope({ kind: "org", id: org.id });

    // effective = 1.0 * (1 - 0.5 * 0.1) = 1.0 * 0.95 = 0.95
    expect(sv.evaluate(scope)).toBeCloseTo(1.0 * (1 - 0.5 * GAMEDEFINES.HEAT_CADRE_PENALTY));

    const bd = sv.breakdown(scope);
    expect(bd.total).toBeCloseTo(sv.evaluate(scope));
    expect(bd.contributors).toHaveLength(2);
    expect(bd.contributors[0]!.label).toBe("Base Cadre");
    expect(bd.contributors[1]!.label).toBe("Heat Penalty");
    expect(bd.contributors[1]!.value).toBeLessThan(0); // penalty is negative
    expect(bd.contributors[1]!.source.kind).toBe("gamedefines");
    // Heat penalty has org heat as sub-contributor
    expect(bd.contributors[1]!.children).toHaveLength(1);
    expect(bd.contributors[1]!.children[0]!.label).toBe("Organization Heat");
  });

  it("org.effective_cadre clamps to 0", () => {
    const org = snap.organizations[0]!;
    org.cadre_level = 0.01;
    org.heat = 100; // absurdly high
    const sv = selectors.get("org.effective_cadre");
    expect(sv.evaluate(makeScope({ kind: "org", id: org.id }))).toBe(0);
  });

  it("hex.imperial_rent distributes total rent by rent_level", () => {
    // Set up 2 territories with known rent levels
    snap.territories = [
      { ...snap.territories[0]!, rent_level: 0.6 },
      { ...snap.territories[1]!, rent_level: 0.4 },
    ];
    snap.derived.imperial_rent = {
      unequal_exchange: 100,
      externalized_reproductive: 50,
      domestic_shadow: 50,
      total: 200,
    };

    const sv = selectors.get("hex.imperial_rent");
    const scopeA = makeScope({ kind: "hex", id: snap.territories[0]!.id });
    const scopeB = makeScope({ kind: "hex", id: snap.territories[1]!.id });

    // Territory A gets 60% of 200 = 120
    expect(sv.evaluate(scopeA)).toBeCloseTo(120);
    // Territory B gets 40% of 200 = 80
    expect(sv.evaluate(scopeB)).toBeCloseTo(80);

    const bd = sv.breakdown(scopeA);
    expect(bd.total).toBeCloseTo(120);
    expect(bd.contributors).toHaveLength(3);
    expect(bd.contributors.map((c) => c.label)).toEqual([
      "Unequal Exchange",
      "Externalized Reproductive",
      "Domestic Shadow",
    ]);
  });

  it("org.consciousness_gap measures material vs consciousness delta", () => {
    const org = snap.organizations[0]!;
    // Link org to the snapshot's territories
    org.territory_ids = snap.territories.map((t) => t.id);
    // Territory heat (proxy for material conditions)
    for (const t of snap.territories) {
      t.heat = 0.8;
    }
    // Org consciousness
    org.consciousness = { liberal: 0.3, fascist: 0.1, revolutionary: 0.6 };

    const sv = selectors.get("org.consciousness_gap");
    const scope = makeScope({ kind: "org", id: org.id });

    // gap = avg_heat (0.8) - revolutionary (0.6) = 0.2
    expect(sv.evaluate(scope)).toBeCloseTo(0.2);

    const bd = sv.breakdown(scope);
    expect(bd.total).toBeCloseTo(0.2);
    expect(bd.contributors).toHaveLength(2);
    expect(bd.contributors[0]!.label).toContain("Material Agitation");
    expect(bd.contributors[1]!.label).toBe("Revolutionary Consciousness");
  });
});
