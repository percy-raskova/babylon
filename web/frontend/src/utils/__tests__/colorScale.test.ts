import { describe, test, expect } from "vitest";
import { metricToColor } from "../colorScale";

describe("metricToColor color scale utility", () => {
  test("returns CRIMSON for low profit_rate", () => {
    // low translates to factor = 0 which is CRIMSON (#8b0000)
    const color = metricToColor(0.01, 0.01, 0.1, "profit_rate");
    expect(color).toBe("#8b0000");
  });

  test("returns GOLD for high profit_rate", () => {
    // high translates to factor = 1 which is GOLD (#daa520)
    const color = metricToColor(0.1, 0.01, 0.1, "profit_rate");
    expect(color).toBe("#daa520");
  });

  test("handles heat metric with ash→crimson→gold gradient", () => {
    const min = 0;
    const max = 100;

    // low
    const colorLow = metricToColor(0, min, max, "heat");
    expect(colorLow).toBe("#808080"); // ASH

    // mid
    const colorMid = metricToColor(50, min, max, "heat");
    expect(colorMid).toBe("#8b0000"); // CRIMSON

    // high
    const colorHigh = metricToColor(100, min, max, "heat");
    expect(colorHigh).toBe("#daa520"); // GOLD
  });

  test("returns BLOOD_VOID for zero org_presence", () => {
    const color = metricToColor(0, 0, 10, "org_presence");
    expect(color).toBe("#1a0005");
  });

  test("handles edge case where min equals max", () => {
    // When min === max, it sets factor to 0.5 (midpoint)
    // For profit_rate, 0.5 is exactly between CRIMSON and GOLD
    const color = metricToColor(5, 5, 5, "profit_rate");
    const colorMid = metricToColor(5, 0, 10, "profit_rate");
    expect(color).toBe(colorMid);
  });
});
