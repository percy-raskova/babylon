import { describe, expect, it } from "vitest";
import type { CrisisPhase, TerritoryState } from "@/types/game";
import {
  CRISIS_IN_PROGRESS_PHASES,
  aggregateCapitalStock,
  aggregateWageCompression,
  crisisPopulationShare,
  peakCrisisPhase,
} from "./CrisisTimeline";

/** Minimal TerritoryState factory — only the fields the aggregators read. */
function terr(overrides: Partial<TerritoryState>): TerritoryState {
  return {
    id: "T",
    name: "T",
    h3_index: null,
    h3_resolution: 8,
    county_fips: "00000",
    heat: 0,
    sector_type: "x",
    territory_type: "x",
    profile: "x",
    rent_level: 0,
    population: 0,
    under_eviction: false,
    biocapacity: 0,
    host_id: null,
    occupant_id: null,
    ...overrides,
  };
}

describe("peakCrisisPhase", () => {
  it("returns null when no territory carries a phase", () => {
    expect(peakCrisisPhase([terr({ population: 100 })])).toBeNull();
  });

  it("returns the deepest phase carried by any territory with population", () => {
    const territories = [
      terr({ population: 100, crisis_phase: "onset" }),
      terr({ population: 100, crisis_phase: "deep" }),
      terr({ population: 100, crisis_phase: "early" }),
    ];
    expect(peakCrisisPhase(territories)).toBe<CrisisPhase>("deep");
  });

  it("treats RECOVERY as less severe than DEEP (lifecycle order)", () => {
    const territories = [
      terr({ population: 100, crisis_phase: "recovery" }),
      terr({ population: 100, crisis_phase: "early" }),
    ];
    expect(peakCrisisPhase(territories)).toBe<CrisisPhase>("early");
  });

  it("ignores phase-bearing territories with zero population (honest weight)", () => {
    const territories = [
      terr({ population: 0, crisis_phase: "deep" }),
      terr({ population: 100, crisis_phase: "onset" }),
    ];
    expect(peakCrisisPhase(territories)).toBe<CrisisPhase>("onset");
  });

  it("returns 'normal' when every populated territory is normal", () => {
    expect(peakCrisisPhase([terr({ population: 50, crisis_phase: "normal" })])).toBe<CrisisPhase>(
      "normal",
    );
  });
});

describe("crisisPopulationShare", () => {
  it("is null when no territory carries a phase", () => {
    expect(crisisPopulationShare([terr({ population: 100 })])).toBeNull();
  });

  it("is the population fraction in onset/early/deep (not recovery/normal)", () => {
    const territories = [
      terr({ population: 300, crisis_phase: "deep" }),
      terr({ population: 100, crisis_phase: "normal" }),
      terr({ population: 100, crisis_phase: "recovery" }),
    ];
    // 300 in-crisis / 500 total phased population = 0.6
    expect(crisisPopulationShare(territories)).toBeCloseTo(0.6, 6);
  });

  it("only every canonical in-progress phase counts toward the numerator", () => {
    for (const phase of CRISIS_IN_PROGRESS_PHASES) {
      expect(crisisPopulationShare([terr({ population: 10, crisis_phase: phase })])).toBe(1);
    }
    expect(crisisPopulationShare([terr({ population: 10, crisis_phase: "recovery" })])).toBe(0);
    expect(crisisPopulationShare([terr({ population: 10, crisis_phase: "normal" })])).toBe(0);
  });
});

describe("aggregateWageCompression", () => {
  it("is null when no territory carries a value", () => {
    expect(aggregateWageCompression([terr({ population: 100 })])).toBeNull();
  });

  it("is the population-weighted mean over territories that carry it", () => {
    const territories = [
      terr({ population: 300, wage_compression: 0.4 }),
      terr({ population: 100, wage_compression: 0.8 }),
    ];
    // (0.4*300 + 0.8*100) / 400 = 0.5
    expect(aggregateWageCompression(territories)).toBeCloseTo(0.5, 6);
  });

  it("falls back to a plain mean when weighted rows carry no population", () => {
    const territories = [
      terr({ population: 0, wage_compression: 0.2 }),
      terr({ population: 0, wage_compression: 0.6 }),
    ];
    expect(aggregateWageCompression(territories)).toBeCloseTo(0.4, 6);
  });

  it("skips non-finite values without fabricating a zero", () => {
    const territories = [
      terr({ population: 100, wage_compression: null }),
      terr({ population: 100, wage_compression: 0.5 }),
    ];
    expect(aggregateWageCompression(territories)).toBeCloseTo(0.5, 6);
  });
});

describe("aggregateCapitalStock", () => {
  it("is null when no territory carries a value", () => {
    expect(aggregateCapitalStock([terr({ population: 100 })])).toBeNull();
  });

  it("is the SUM of capital_stock (extensive quantity, not a mean)", () => {
    const territories = [
      terr({ population: 1, capital_stock: 1_000 }),
      terr({ population: 1, capital_stock: 2_500 }),
    ];
    expect(aggregateCapitalStock(territories)).toBe(3_500);
  });

  it("ignores non-finite entries", () => {
    const territories = [
      terr({ capital_stock: null }),
      terr({ capital_stock: 42 }),
      terr({ capital_stock: Number.NaN }),
    ];
    expect(aggregateCapitalStock(territories)).toBe(42);
  });
});
