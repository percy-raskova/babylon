/**
 * Unit tests for MapLegend v2, adapted (spec-113 Lane B) to a
 * `legend: LensLegend` + `label` prop pair instead of a bare `lens: Lens`.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MapLegend } from "./MapLegend";
import { DATA_RAMPS } from "@/theme/colors";
import { LENS_REGISTRY } from "@/lib/lenses/registry";

describe("MapLegend", () => {
  it("renders a ramp swatch strip + legend text for a ramp legend", () => {
    render(<MapLegend legend={{ kind: "ramp", stops: DATA_RAMPS.heat }} label="Heat" />);
    expect(screen.getByTestId("map-legend")).toBeInTheDocument();
    expect(screen.getByTestId("map-legend")).toHaveTextContent(/heat/i);
    expect(screen.getByTestId("map-legend")).toHaveAttribute("data-legend-kind", "ramp");
  });

  it("renders nothing for a none legend", () => {
    render(<MapLegend legend={{ kind: "none" }} label="Nothing" />);
    expect(screen.queryByTestId("map-legend")).not.toBeInTheDocument();
  });

  it("renders a categorical swatch list for a categorical legend", () => {
    const stanceDef = LENS_REGISTRY.find((d) => d.id === "stance")!;
    render(<MapLegend legend={stanceDef.legend} label={stanceDef.label} />);
    const legend = screen.getByTestId("map-legend");
    expect(legend).toHaveAttribute("data-legend-kind", "categorical");
    expect(legend).toHaveTextContent(/uphold/i);
    expect(legend).toHaveTextContent(/ignore/i);
    expect(legend).toHaveTextContent(/abolish/i);
  });

  it("class_composition's categorical legend lists every social role", () => {
    const def = LENS_REGISTRY.find((d) => d.id === "class_composition")!;
    render(<MapLegend legend={def.legend} label={def.label} />);
    expect(screen.getByTestId("map-legend")).toHaveTextContent(/core bourgeoisie/i);
  });

  it("draws a marker at the current-value position when provided (ramp mode only)", () => {
    render(
      <MapLegend
        legend={{ kind: "ramp", stops: DATA_RAMPS.heat }}
        label="Heat"
        currentValue={0.5}
      />,
    );
    expect(screen.getByTestId("map-legend-marker")).toHaveStyle({ left: "50%" });
  });

  it("omits the marker when currentValue is null (honest no-data, per Constitution III.11)", () => {
    render(
      <MapLegend
        legend={{ kind: "ramp", stops: DATA_RAMPS.heat }}
        label="Heat"
        currentValue={null}
      />,
    );
    expect(screen.queryByTestId("map-legend-marker")).not.toBeInTheDocument();
  });

  it("does not draw a marker for a categorical legend even if currentValue is passed", () => {
    const stanceDef = LENS_REGISTRY.find((d) => d.id === "stance")!;
    render(<MapLegend legend={stanceDef.legend} label={stanceDef.label} currentValue={0.5} />);
    expect(screen.queryByTestId("map-legend-marker")).not.toBeInTheDocument();
  });

  it("marks data-flash=true when the flash prop is set (domain rescale event)", () => {
    render(
      <MapLegend legend={{ kind: "ramp", stops: DATA_RAMPS.heat }} label="Heat" flash={true} />,
    );
    expect(screen.getByTestId("map-legend")).toHaveAttribute("data-flash", "true");
  });

  it("marks data-muted=true when muted (honest empty — ramp carries no signal this tick)", () => {
    // The map-legend-empty-hint (MapControls) sets this when a ramp lens has no
    // usable value: the strip dims to read as inactive rather than as a live 0→1
    // scale nothing sits on (Constitution III.11 — visibly distinct from real data).
    render(
      <MapLegend legend={{ kind: "ramp", stops: DATA_RAMPS.heat }} label="Heat" muted={true} />,
    );
    expect(screen.getByTestId("map-legend")).toHaveAttribute("data-muted", "true");
  });

  it("is not muted by default", () => {
    render(<MapLegend legend={{ kind: "ramp", stops: DATA_RAMPS.heat }} label="Heat" />);
    expect(screen.getByTestId("map-legend")).toHaveAttribute("data-muted", "false");
  });
});
