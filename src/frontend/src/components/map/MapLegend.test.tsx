/**
 * Unit tests for MapLegend, adapted (spec-110 B2) to a `lens: Lens` prop.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MapLegend } from "./MapLegend";

describe("MapLegend", () => {
  it("renders a ramp swatch strip + legend text for a metric-ramp lens", () => {
    render(<MapLegend lens={{ kind: "heat" }} />);
    expect(screen.getByTestId("map-legend")).toBeInTheDocument();
    expect(screen.getByTestId("map-legend")).toHaveTextContent(/heat/i);
  });

  it("renders for a metric-kind lens too", () => {
    render(<MapLegend lens={{ kind: "metric", metric: "profit_rate" }} />);
    expect(screen.getByTestId("map-legend")).toHaveTextContent(/profit/i);
  });

  it("renders nothing (no ramp) for balkanization-derived lenses (stance/faction/collapse)", () => {
    render(<MapLegend lens={{ kind: "stance" }} />);
    expect(screen.queryByTestId("map-legend")).not.toBeInTheDocument();
  });
});
