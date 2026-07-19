import { describe, expect, it } from "vitest";
import { makeEconomyDashboardPayload } from "@/test/fixtures";
import {
  deriveFundamentalTheoremReading,
  fundamentalTheoremNarrative,
  sortRegionsByGapDescending,
} from "@/lib/fundamentalTheorem";

describe("deriveFundamentalTheoremReading", () => {
  it("reads wc/vc/gap straight off the dashboard payload", () => {
    const payload = makeEconomyDashboardPayload({
      wage_flow_total: 30,
      value_produced: 100,
      imperial_rent_gap: -70,
    });

    const reading = deriveFundamentalTheoremReading(payload);

    expect(reading).toEqual({ wc: 30, vc: 100, gap: -70, hasSubsidy: false });
  });

  it("flags hasSubsidy when the gap is positive (core wages exceed value produced)", () => {
    const payload = makeEconomyDashboardPayload({
      wage_flow_total: 150,
      value_produced: 100,
      imperial_rent_gap: 50,
    });

    const reading = deriveFundamentalTheoremReading(payload);

    expect(reading?.hasSubsidy).toBe(true);
  });

  it("is null when the graph has no economic activity yet", () => {
    const payload = makeEconomyDashboardPayload({ has_data: false });

    expect(deriveFundamentalTheoremReading(payload)).toBeNull();
  });
});

describe("fundamentalTheoremNarrative", () => {
  it("names the subsidy when core wages exceed value produced", () => {
    const text = fundamentalTheoremNarrative({ wc: 150, vc: 100, gap: 50, hasSubsidy: true });

    expect(text).toContain("150.0");
    expect(text).toContain("100.0");
    expect(text).toContain("imperial subsidy");
  });

  it("states no subsidy applies when the gap is non-positive", () => {
    const text = fundamentalTheoremNarrative({ wc: 30, vc: 100, gap: -70, hasSubsidy: false });

    expect(text).toContain("No aggregate imperial subsidy");
    expect(text).toContain("-70.0");
  });
});

describe("sortRegionsByGapDescending", () => {
  it("orders the worst subsidy (largest positive gap) first", () => {
    const rows = [
      {
        territory_id: "T1",
        population: 100,
        wc_per_capita: 0.1,
        vc_per_capita: 0.5,
        gap_per_capita: -0.4,
      },
      {
        territory_id: "T2",
        population: 200,
        wc_per_capita: 0.9,
        vc_per_capita: 0.2,
        gap_per_capita: 0.7,
      },
      {
        territory_id: "T3",
        population: 50,
        wc_per_capita: 0.3,
        vc_per_capita: 0.3,
        gap_per_capita: 0.0,
      },
    ];

    const sorted = sortRegionsByGapDescending(rows);

    expect(sorted.map((r) => r.territory_id)).toEqual(["T2", "T3", "T1"]);
  });

  it("does not mutate the input array", () => {
    const rows = [
      {
        territory_id: "T1",
        population: 100,
        wc_per_capita: 0,
        vc_per_capita: 0,
        gap_per_capita: 1,
      },
      {
        territory_id: "T2",
        population: 100,
        wc_per_capita: 0,
        vc_per_capita: 0,
        gap_per_capita: 2,
      },
    ];
    const original = [...rows];

    sortRegionsByGapDescending(rows);

    expect(rows).toEqual(original);
  });
});
