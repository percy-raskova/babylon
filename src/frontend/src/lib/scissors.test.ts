import { describe, expect, it } from "vitest";
import { makeTimeseriesPayload } from "@/test/fixtures";
import {
  deriveCorrectionTicks,
  deriveTickerState,
  latestMeltDrift,
  meltCopy,
} from "@/lib/scissors";

describe("deriveCorrectionTicks", () => {
  it("marks the ticks where the cumulative count increments", () => {
    const payload = makeTimeseriesPayload({
      ticks: [0, 1, 2, 3, 4],
      market_corrections: [0, 0, 1, 1, 2],
    });
    expect(deriveCorrectionTicks(payload)).toEqual([2, 4]);
  });

  it("carries the count across null gaps without inventing a snap", () => {
    const payload = makeTimeseriesPayload({
      ticks: [0, 1, 2, 3],
      market_corrections: [0, 1, null, 1],
    });
    expect(deriveCorrectionTicks(payload)).toEqual([1]);
  });

  it("reads a pre-Phase-2 payload (array absent) as no corrections", () => {
    const payload = makeTimeseriesPayload({ market_corrections: undefined });
    expect(deriveCorrectionTicks(payload)).toEqual([]);
  });
});

describe("latestMeltDrift", () => {
  it("is the last non-null price_index minus one", () => {
    const payload = makeTimeseriesPayload({ price_index: [1.0, 1.08, null] });
    expect(latestMeltDrift(payload)).toBeCloseTo(0.08);
  });

  it("is null when the axis never computed", () => {
    const payload = makeTimeseriesPayload({ price_index: [null, null] });
    expect(latestMeltDrift(payload)).toBeNull();
  });
});

describe("deriveTickerState", () => {
  it("stays dark before the axis exists (no phenomenal form without substance)", () => {
    const payload = makeTimeseriesPayload({ fictitious_ratio: [null, null] });
    expect(deriveTickerState(payload)).toBeNull();
  });

  it("reads euphoria at a 30%+ claims overhang", () => {
    const state = deriveTickerState(makeTimeseriesPayload({ fictitious_ratio: [1.0, 1.31] }));
    expect(state?.tone).toBe("euphoria");
    expect(state?.index).toBe(13100);
  });

  it("reads a rally on rising claims below the euphoria line", () => {
    const state = deriveTickerState(makeTimeseriesPayload({ fictitious_ratio: [1.0, 1.1] }));
    expect(state?.tone).toBe("rally");
  });

  it("reads the crash when the latest tick is a snap tick", () => {
    const state = deriveTickerState(
      makeTimeseriesPayload({
        ticks: [0, 1],
        fictitious_ratio: [1.31, 1.05],
        market_corrections: [0, 1],
      }),
    );
    expect(state?.tone).toBe("crash");
    expect(state?.headline).toMatch(/SNAP/);
  });

  it("reads steady on a flat market", () => {
    const state = deriveTickerState(
      makeTimeseriesPayload({ price_index: [1.0, 1.0], fictitious_ratio: [1.0, 1.0] }),
    );
    expect(state?.tone).toBe("steady");
  });

  it("is deterministic — same payload, same state", () => {
    const payload = makeTimeseriesPayload({ fictitious_ratio: [1.0, 1.31] });
    expect(deriveTickerState(payload)).toEqual(deriveTickerState(payload));
  });
});

describe("meltCopy", () => {
  it("reads 'less labor' on a positive drift", () => {
    expect(meltCopy(0.08)).toBe(
      "MELT drift +8.0% — $1 commands 8.0% less labor than its value basis",
    );
  });

  it("reads 'more labor' on a negative drift", () => {
    expect(meltCopy(-0.05)).toBe(
      "MELT drift -5.0% — $1 commands 5.0% more labor than its value basis",
    );
  });
});
