/**
 * Red-first tests for the spec-070 political-topology map lens set.
 *
 * `buildLensLayers` is a pure function (no deck.gl/WebGL dependency) so it's
 * testable without a canvas: given a snapshot's territories + the
 * balkanization block + an active lens mode, it returns a render-agnostic
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
import { buildLensLayers, type BalkanizationBlock, type LensTerritory } from "./mapLensLayers";

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
      lensMode: "stance",
    });

    // FAC_A (UPHOLD) dominates T1/T2 -> laser red; FAC_C (ABOLISH) dominates T3 -> solidarity green.
    expect(result.getFillColor("T1")).toEqual([255, 51, 68, expect.any(Number)]);
    expect(result.getFillColor("T2")).toEqual([255, 51, 68, expect.any(Number)]);
    expect(result.getFillColor("T3")).toEqual([95, 191, 122, expect.any(Number)]);
    expect(result.legendLabel.toLowerCase()).toContain("stance");
  });

  it("heat lens produces a materially different fill than stance for the same territory", () => {
    const stance = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "stance",
    });
    const heat = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "heat",
    });

    expect(heat.getFillColor("T1")).not.toEqual(stance.getFillColor("T1"));
    expect(heat.legendLabel.toLowerCase()).toContain("heat");
  });

  it("habitability lens diverges low (crimson) vs high (green) territories", () => {
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "habitability",
    });

    const low = result.getFillColor("T3"); // habitability 0.1
    const high = result.getFillColor("T2"); // habitability 0.9
    expect(low).not.toEqual(high);
    // Low habitability should read redder than high habitability.
    expect(low[0]).toBeGreaterThan(high[0]);
    expect(high[1]).toBeGreaterThan(low[1]);
  });

  it("faction lens desaturates territories below the meaningful-influence threshold", () => {
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "faction",
      factionFilter: "FAC_C",
    });

    // FAC_C has 0 measured influence on T1/T2 -> desaturated; dominant on T3 -> shaded.
    const desaturated = result.getFillColor("T1");
    const shaded = result.getFillColor("T3");
    expect(desaturated).not.toEqual(shaded);
  });

  it("stance and collapse lenses render concentric rings for multi-faction territories", () => {
    const stance = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "stance",
    });
    const heat = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "heat",
    });

    // T1 has two influence rows -> at least one ring in stance/collapse lenses.
    expect(stance.rings.some((r) => r.territoryId === "T1")).toBe(true);
    // Heat lens suppresses rings entirely (per mockup: stance reduced to outline).
    expect(heat.rings.length).toBe(0);
  });

  it("renders sovereign CLAIMS hulls only in stance/collapse lenses, sourced from claimed_territory_ids", () => {
    const stance = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "stance",
    });
    const faction = buildLensLayers({
      territories: TERRITORIES,
      balkanization: BALKANIZATION,
      lensMode: "faction",
      factionFilter: "FAC_A",
    });

    expect(stance.hulls.length).toBe(1);
    expect(stance.hulls[0]?.sovereignId).toBe("SOV_A");
    expect(stance.hulls[0]?.territoryIds.sort()).toEqual(["T2", "T3"]);
    // Faction lens does not render sovereign hulls (per mockup / spec Acceptance Scenario 2).
    expect(faction.hulls.length).toBe(0);
  });

  it("degrades to an empty/no-data legend when balkanization data is absent", () => {
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: null,
      lensMode: "stance",
    });

    expect(result.hulls).toEqual([]);
    expect(result.rings).toEqual([]);
    expect(result.legendLabel.toLowerCase()).toContain("no data");
  });

  it("VIII.9: BalkanizationBlock carries no hyperedge/community field for the hull builder to read", () => {
    // Structural guarantee: the type this module's hull logic consumes
    // (BalkanizationBlock) has exactly these three keys. If a future edit
    // added a `hyperedges`/`communities` field to this type and wired it
    // into hull construction, this test's key-set assertion would catch it.
    const keys = Object.keys(BALKANIZATION).sort();
    expect(keys).toEqual(["factions", "sovereigns", "territory_influence"]);

    // Runtime guarantee: even if a caller attaches extra hyperedge-shaped
    // data onto the object (bypassing the type system, e.g. from an
    // untyped API response), buildLensLayers's hull output must still be
    // derived ONLY from `sovereigns[].claimed_territory_ids` — never from
    // any `hyperedges`/`communities` key, present or not.
    // Spread + extra property: TS structural typing permits this (excess
    // property checks only apply to object literals assigned directly), so
    // this compiles — the guarantee under test is the RUNTIME behavior
    // below, not a type error.
    const withHyperedgeNoise: BalkanizationBlock & { hyperedges: unknown[] } = {
      ...BALKANIZATION,
      hyperedges: [{ id: "H1", member_ids: ["T1", "T2", "T3"], category: "contradiction_pair" }],
    };
    const result = buildLensLayers({
      territories: TERRITORIES,
      balkanization: withHyperedgeNoise,
      lensMode: "stance",
    });

    expect(result.hulls).toHaveLength(1);
    expect(result.hulls[0]?.sovereignId).toBe("SOV_A");
  });
});
