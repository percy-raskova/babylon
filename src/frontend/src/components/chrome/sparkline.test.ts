import { describe, expect, it } from "vitest";
import { sparklinePoints, sparklineSeries } from "./sparkline";

describe("sparklineSeries", () => {
  it("skips null/undefined entries without interpolating", () => {
    expect(sparklineSeries([null, 1, undefined, 3])).toEqual([
      { x: 1, y: 1 },
      { x: 3, y: 3 },
    ]);
  });
});

describe("sparklinePoints", () => {
  it("returns null below two real points — a lone value is not a trend", () => {
    expect(sparklinePoints([], 60, 16)).toBeNull();
    expect(sparklinePoints([null, null], 60, 16)).toBeNull();
    expect(sparklinePoints([null, 0.5], 60, 16)).toBeNull();
  });

  it("scales points into the box, preserving tick order and gaps", () => {
    expect(sparklinePoints([0, null, 1], 60, 16)).toBe("1.0,15.0 59.0,1.0");
  });

  it("handles a flat series without dividing by zero", () => {
    expect(sparklinePoints([0.5, 0.5], 60, 16)).toBe("1.0,15.0 59.0,15.0");
  });
});
