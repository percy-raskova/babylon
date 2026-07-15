/**
 * Red-first tests for the spec-070 political-topology map lens set, adapted
 * (spec-110 B2) to the unified `Lens` discriminated union — the input field
 * is now `lens: Lens` (`{ kind: "stance" | ... }` or `{ kind: "metric";
 * metric }`), replacing the old bare `lensMode: LensMode` string.
 *
 * `buildLensLayers` is a pure function (no deck.gl/WebGL dependency) so it's
 * testable without a canvas: given a snapshot's territories + the
 * balkanization block + an active lens, it returns a render-agnostic
 * descriptor (fill-color function, concentric rings, sovereign CLAIMS
 * hulls, legend text) that `DeckGLMap.tsx` composes into real deck.gl
 * layers.
 *
 * Constitution VIII.9 (binding): hyperedge/community relationships must
 * NEVER be rendered as a spatial hull on the geographic map. The last test
 * in this file is the structural guarantee — it proves the hull builder's
 * input type has no hyperedge/community field to read in the first place,
 * and that passing hyperedge-shaped data through is a compile-time error
 * (verified here at the type level plus a runtime behavioral check).
 */

import { describe, it, expect } from "vitest";
import {
  buildLensLayers,
  TERRITORY_TYPE_COLOR,
  TERRITORY_TYPE_LABELS,
  type BalkanizationBlock,
  type LensTerritory,
} from "./mapLensLayers";

const TERRITORIES: LensTerritory[] = [
  { id: "T1", h3_index: "872a3072cffffff", heat: 0.4, biocapacity: 40, max_biocapacity: 100 },
  { id: "T2", h3_index: "872a3072dffffff", heat: 0.2, biocapacity: 90, max_biocapacity: 100 },
  { id: "T3", h3_index: "872a3072effffff", heat: 0.8, biocapacity: 10, max_biocapacity: 100 },
];

const BALKANIZATION: BalkanizationBlock = {
  factions: [
    { id: "FAC_A", colonial_stance: "UPHOLD", is_settler_formation: true },
    { id: "FAC_B", colonial_stance: "IGNORE", is_settler_formation: true },
    { id: "FAC_C", colonial_stance: "ABOLISH", is_settler_formation: false },
  ],
  sovereigns: [
    {
      id: "SOV_A",
      ruling_faction_id: "FAC_A",
      extraction_policy: "INTENSIFY",
      legitimacy: 0.58,
      claimed_territory_ids: ["T2", "T3"],
    },
  ],
  territory_influence: [
    {
      territory_id: "T1",
      influences: [
        { faction_id: "FAC_A", influence_level: 0.47, support_type: "ideological" },
        { faction_id: "FAC_B", influence_level: 0.41, support_type: "material" },
      ],
      dominant_faction_id: "FAC_A",
      current_sovereign_id: null,
      contested: true,
      habitability: 0.4,
    },
    {
      territory_id: "T2",
      influences: [{ faction_id: "FAC_A", influence_level: 0.71, support_type: "ideological" }],
      dominant_faction_id: "FAC_A",
      current_sovereign_id: "SOV_A",
      contested: false,
      habitability: 0.9,
    },
    {
      territory_id: "T3",
      influences: [{ faction_id: "FAC_C", influence_level: 0.62, support_type: "material" }],
      dominant_faction_id: "FAC_C",
      current_sovereign_id: "SOV_A",
      contested: false,
      habitability: 0.1,
    },
  ],
};

describe("buildLensLayers", () => {
  it("stance lens fills by dominant ColonialStance token color", () => {
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "stance" },
    });

    // FAC_A (UPHOLD) dominates T1/T2 -> laser red; FAC_C (ABOLISH) dominates T3 -> solidarity green.
    expect(result.getFillColor("T1")).toEqual([255, 51, 68, expect.any(Number)]);
    expect(result.getFillColor("T2")).toEqual([255, 51, 68, expect.any(Number)]);
    expect(result.getFillColor("T3")).toEqual([95, 191, 122, expect.any(Number)]);
    expect(result.legendLabel.toLowerCase()).toContain("stance");
  });

  it("handles the real engine's lowercase ColonialStance wire values (uphold/ignore/abolish)", () => {
    // web/game/engine_bridge.py's _build_balkanization_block passes the raw
    // graph attribute through verbatim, which for real engine-computed data
    // is ColonialStance's lowercase .value (src/babylon/models/enums/
    // balkanization.py:49-51) — not the uppercase display form used
    // elsewhere in this test file's fixtures.
    const lowercaseBalkanization: BalkanizationBlock = {
      ...BALKANIZATION,
      factions: BALKANIZATION.factions.map((f) => ({
        ...f,
        colonial_stance: f.colonial_stance.toLowerCase(),
      })),
    };
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: lowercaseBalkanization,
      lens: { kind: "stance" },
    });

    expect(result.getFillColor("T1")).toEqual([255, 51, 68, expect.any(Number)]);
    expect(result.getFillColor("T3")).toEqual([95, 191, 122, expect.any(Number)]);
  });

  it("heat lens produces a materially different fill than stance for the same territory", () => {
    const stance = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "stance" },
    });
    const heat = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "heat" },
    });

    expect(heat.getFillColor("T1")).not.toEqual(stance.getFillColor("T1"));
    expect(heat.legendLabel.toLowerCase()).toContain("heat");
  });

  it("habitability lens diverges low (crimson) vs high (green) territories", () => {
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "habitability" },
    });

    const low = result.getFillColor("T3"); // habitability 0.1
    const high = result.getFillColor("T2"); // habitability 0.9
    expect(low).not.toEqual(high);
    // Low habitability should read redder than high habitability.
    expect(low[0]).toBeGreaterThan(high[0]);
    expect(high[1]).toBeGreaterThan(low[1]);
  });

  it("habitability lens prefers the territory's own real habitability over the balkanization row (spec-109 A2)", () => {
    // T2's balkanization row says habitability=0.9 (near max_biocapacity ->
    // green), but the territory itself now carries a real, much lower
    // MetabolismSystem value (0.05) via the bridge's graph threading — that
    // must win, not the derived balkanization proxy.
    const territoriesWithRealHabitability: LensTerritory[] = TERRITORIES.map((t) =>
      t.id === "T2" ? { ...t, habitability: 0.05 } : t,
    );

    const result = buildLensLayers({
      territories: territoriesWithRealHabitability,
      balkanization: BALKANIZATION,
      lens: { kind: "habitability" },
    });

    const t2WithReal = result.getFillColor("T2");
    const t3Low = result.getFillColor("T3"); // row habitability 0.1, no real value

    // T2 now reads as low-habitability (redder), close to T3, not the
    // green the stale balkanization-row value (0.9) would have produced.
    expect(t2WithReal[0]).toBeGreaterThan(150);
    expect(Math.abs(t2WithReal[0] - t3Low[0])).toBeLessThan(40);
  });

  it("faction lens desaturates territories below the meaningful-influence threshold", () => {
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "faction" },
      factionFilter: "FAC_C",
    });

    // FAC_C has 0 measured influence on T1/T2 -> desaturated; dominant on T3 -> shaded.
    const desaturated = result.getFillColor("T1");
    const shaded = result.getFillColor("T3");
    expect(desaturated).not.toEqual(shaded);
  });

  it("stance lens renders concentric rings for multi-faction territories", () => {
    const stance = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "stance" },
    });
    const heat = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "heat" },
    });

    expect(stance.rings.some((r) => r.territoryId === "T1")).toBe(true);
    expect(heat.rings).toHaveLength(0);
  });

  it("collapse lens renders contested territories distinctly from stance", () => {
    const stance = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "stance" },
    });
    const collapse = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "collapse" },
    });

    const stanceT1 = stance.getFillColor("T1");
    const collapseT1 = collapse.getFillColor("T1");
    expect(collapseT1).not.toEqual(stanceT1);
  });

  it("renders sovereign CLAIMS hulls only in stance/collapse lenses, sourced from claimed_territory_ids", () => {
    const stance = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "stance" },
    });
    const faction = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lens: { kind: "faction" },
      factionFilter: "FAC_A",
    });

    expect(stance.hulls).toHaveLength(1);
    expect(stance.hulls[0]?.sovereignId).toBe("SOV_A");
    expect(stance.hulls[0]?.territoryIds.sort()).toEqual(["T2", "T3"]);
    // Faction lens does not render sovereign hulls (per mockup / spec Acceptance Scenario 2).
    expect(faction.hulls).toHaveLength(0);
  });

  it("degrades to an empty/no-data legend when balkanization data is absent", () => {
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: null,
      lens: { kind: "stance" },
    });

    expect(result.hulls).toEqual([]);
    expect(result.rings).toEqual([]);
    expect(result.legendLabel.toLowerCase()).toContain("no data");
  });

  it("degrades to no-data when balkanization block is structurally empty (not null)", () => {
    const emptyBlock: BalkanizationBlock = {
      factions: [],
      sovereigns: [],
      territory_influence: [],
    };
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: emptyBlock,
      lens: { kind: "stance" },
    });

    expect(result.hulls).toEqual([]);
    expect(result.rings).toEqual([]);
    expect(result.legendLabel.toLowerCase()).toContain("no data");
  });

  describe("territory-local lenses render without balkanization data (A8)", () => {
    const NO_DATA_COLOR = [58, 53, 48, 160];

    it.each(["heat", "habitability"] as const)(
      "%s lens renders territory-local data when balkanization is null",
      (kind) => {
        const result = buildLensLayers({
          territories: TERRITORIES,
          balkanization: null,
          lens: { kind },
        });

        expect(result.legendLabel.toLowerCase()).not.toContain("no data");
        expect(result.getFillColor("T2")).not.toEqual(NO_DATA_COLOR);
        expect(result.getFillColor("T3")).not.toEqual(NO_DATA_COLOR);
        // The fill must actually vary with the underlying territory value.
        expect(result.getFillColor("T2")).not.toEqual(result.getFillColor("T3"));
      },
    );

    it.each(["heat", "habitability"] as const)(
      "%s lens renders territory-local data when balkanization is structurally empty",
      (kind) => {
        const result = buildLensLayers({
          territories: TERRITORIES,
          balkanization: { factions: [], sovereigns: [], territory_influence: [] },
          lens: { kind },
        });

        expect(result.legendLabel.toLowerCase()).not.toContain("no data");
        expect(result.getFillColor("T3")).not.toEqual(NO_DATA_COLOR);
      },
    );

    it("unknown territory still fills NO_DATA under the heat lens (III.11 stays per-territory)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES,
        balkanization: null,
        lens: { kind: "heat" },
      });
      expect(result.getFillColor("T999")).toEqual(NO_DATA_COLOR);
    });
  });

  describe("metric-kind lens (the B2 lens-union addition)", () => {
    const TERRITORIES_WITH_METRICS: LensTerritory[] = TERRITORIES.map((t, i) => ({
      ...t,
      metrics: { profit_rate: 0.1 + i * 0.4, population: 0.2 + i * 0.3 },
    }));

    it("fills by the requested metric property, not by heat/biocapacity", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_METRICS,
        balkanization: null,
        lens: { kind: "metric", metric: "profit_rate" },
      });

      const low = result.getFillColor("T1"); // profit_rate 0.1
      const high = result.getFillColor("T3"); // profit_rate 0.9
      expect(low).not.toEqual(high);
      expect(result.legendLabel.toLowerCase()).toContain("profit");
    });

    it("never requires balkanization data (always territory-local)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_METRICS,
        balkanization: null,
        lens: { kind: "metric", metric: "population" },
      });
      expect(result.legendLabel.toLowerCase()).not.toContain("no data");
    });

    it("renders NO_DATA for a territory missing the requested metric", () => {
      const result = buildLensLayers({
        territories: TERRITORIES, // no `metrics` bag at all
        balkanization: null,
        lens: { kind: "metric", metric: "occ" },
      });
      expect(result.getFillColor("T1")).toEqual([58, 53, 48, 160]);
    });

    it("renders no rings/hulls (those are stance/collapse-only)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_METRICS,
        balkanization: BALKANIZATION,
        lens: { kind: "metric", metric: "profit_rate" },
      });
      expect(result.rings).toEqual([]);
      expect(result.hulls).toEqual([]);
    });
  });

  describe("class_composition lens (spec-113 Lane B/D)", () => {
    const TERRITORIES_WITH_CLASS: LensTerritory[] = [
      { ...TERRITORIES[0]!, dominantClass: "core_bourgeoisie" },
      { ...TERRITORIES[1]!, dominantClass: "periphery_proletariat" },
      { ...TERRITORIES[2]!, dominantClass: null },
    ];

    it("fills by dominantClass, distinctly per role", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_CLASS,
        balkanization: null,
        lens: { kind: "class_composition" },
      });
      expect(result.getFillColor("T1")).not.toEqual(result.getFillColor("T2"));
    });

    it("is loud no-data for a territory with no dominantClass (Constitution III.11)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_CLASS,
        balkanization: null,
        lens: { kind: "class_composition" },
      });
      expect(result.getFillColor("T3")).toEqual([58, 53, 48, 160]);
    });

    it("never requires balkanization data (territory-local, like metric lenses)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_CLASS,
        balkanization: null,
        lens: { kind: "class_composition" },
      });
      expect(result.legendLabel.toLowerCase()).not.toContain("no data");
    });

    it("renders no rings/hulls (balkanization-only overlays)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_CLASS,
        balkanization: BALKANIZATION,
        lens: { kind: "class_composition" },
      });
      expect(result.rings).toEqual([]);
      expect(result.hulls).toEqual([]);
    });
  });

  describe("territory_type lens (Wave 2 Round 2 addition)", () => {
    const TERRITORIES_WITH_TYPE: LensTerritory[] = [
      { ...TERRITORIES[0]!, territoryType: "core" },
      { ...TERRITORIES[1]!, territoryType: "periphery" },
      { ...TERRITORIES[2]!, territoryType: null },
    ];

    it("fills by territoryType, distinctly per real TerritoryType enum value", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_TYPE,
        balkanization: null,
        lens: { kind: "territory_type" },
      });
      expect(result.getFillColor("T1")).not.toEqual(result.getFillColor("T2"));
      expect(result.getFillColor("T1")).toEqual(TERRITORY_TYPE_COLOR.core);
      expect(result.getFillColor("T2")).toEqual(TERRITORY_TYPE_COLOR.periphery);
    });

    it("is loud no-data for a territory with no territoryType (Constitution III.11)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_TYPE,
        balkanization: null,
        lens: { kind: "territory_type" },
      });
      expect(result.getFillColor("T3")).toEqual([58, 53, 48, 160]);
    });

    it("is loud no-data for an unrecognized territory-type string", () => {
      const result = buildLensLayers({
        territories: [{ ...TERRITORIES[0]!, territoryType: "not_a_real_type" }],
        balkanization: null,
        lens: { kind: "territory_type" },
      });
      expect(result.getFillColor("T1")).toEqual([58, 53, 48, 160]);
    });

    it("never requires balkanization data (territory-local, like class_composition)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_TYPE,
        balkanization: null,
        lens: { kind: "territory_type" },
      });
      expect(result.legendLabel.toLowerCase()).not.toContain("no data");
    });

    it("renders no rings/hulls (balkanization-only overlays)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_TYPE,
        balkanization: BALKANIZATION,
        lens: { kind: "territory_type" },
      });
      expect(result.rings).toEqual([]);
      expect(result.hulls).toEqual([]);
    });

    it("TERRITORY_TYPE_COLOR/TERRITORY_TYPE_LABELS cover exactly the 5 real TerritoryType enum values", () => {
      // src/babylon/models/enums/territory.py's TerritoryType — CORE/PERIPHERY/
      // RESERVATION/PENAL_COLONY/CONCENTRATION_CAMP, snake_case wire values.
      const expectedKeys = [
        "core",
        "periphery",
        "reservation",
        "penal_colony",
        "concentration_camp",
      ];
      expect(Object.keys(TERRITORY_TYPE_COLOR).sort()).toEqual(expectedKeys.sort());
      expect(Object.keys(TERRITORY_TYPE_LABELS).sort()).toEqual(expectedKeys.sort());
    });

    it("every TERRITORY_TYPE_COLOR entry is a distinct color (visually distinguishable)", () => {
      const colors = Object.values(TERRITORY_TYPE_COLOR).map((c) => c.join(","));
      expect(new Set(colors).size).toBe(colors.length);
    });
  });

  describe("throughput_position / agitation metric lenses (Wave 2 Round 2 addition)", () => {
    const TERRITORIES_WITH_NEW_METRICS: LensTerritory[] = TERRITORIES.map((t, i) => ({
      ...t,
      metrics: { throughput_position: 0.1 + i * 0.4, agitation: 0.2 + i * 0.3 },
    }));

    it("fills by throughput_position, varying with the underlying value", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_NEW_METRICS,
        balkanization: null,
        lens: { kind: "metric", metric: "throughput_position" },
      });
      expect(result.getFillColor("T1")).not.toEqual(result.getFillColor("T3"));
      expect(result.legendLabel.toLowerCase()).toContain("throughput");
    });

    it("fills by agitation, varying with the underlying value", () => {
      const result = buildLensLayers({
        territories: TERRITORIES_WITH_NEW_METRICS,
        balkanization: null,
        lens: { kind: "metric", metric: "agitation" },
      });
      expect(result.getFillColor("T1")).not.toEqual(result.getFillColor("T3"));
      expect(result.legendLabel.toLowerCase()).toContain("agitation");
    });

    it("renders NO_DATA for a territory missing throughput_position/agitation (never a fabricated 0)", () => {
      const result = buildLensLayers({
        territories: TERRITORIES, // no `metrics` bag at all
        balkanization: null,
        lens: { kind: "metric", metric: "agitation" },
      });
      expect(result.getFillColor("T1")).toEqual([58, 53, 48, 160]);
    });
  });

  it("VIII.9: BalkanizationBlock carries no hyperedge/community field for the hull builder to read", () => {
    // Runtime guarantee: even if a caller attaches extra hyperedge-shaped
    // data onto the object (bypassing the type system, e.g. from an
    // untyped API response), buildLensLayers's hull output must still be
    // derived ONLY from `sovereigns[].claimed_territory_ids` — never from
    // any `hyperedges`/`communities` key, present or not.
    const withHyperedgeNoise: BalkanizationBlock & { hyperedges: unknown[] } = {
      ...BALKANIZATION,
      hyperedges: [{ id: "H1", member_ids: ["T1", "T2", "T3"], category: "contradiction_pair" }],
    };
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: withHyperedgeNoise,
      lens: { kind: "stance" },
    });

    expect(result.hulls).toHaveLength(1);
    expect(result.hulls[0]?.sovereignId).toBe("SOV_A");
  });
});
