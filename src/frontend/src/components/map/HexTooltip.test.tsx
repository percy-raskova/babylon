/**
 * Unit tests for HexTooltip, adapted (spec-110 B2) to take the active
 * `Lens` as a prop (instead of `uiStore.activeLens` + the old
 * `LensId`-keyed `lensDefinitions.ts` priority table — that analytical-lens
 * concept is a third, unrelated axis this lane doesn't touch; see the
 * B2 report for why it wasn't ported).
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HexTooltip } from "./HexTooltip";
import { makeTerritory } from "@/test/fixtures";

describe("HexTooltip", () => {
  it("renders the territory name and lens label", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ name: "Downtown" })}
        x={10}
        y={20}
        lens={{ kind: "heat" }}
      />,
    );
    expect(screen.getByText("Downtown")).toBeInTheDocument();
    expect(screen.getAllByText(/heat/i).length).toBeGreaterThan(0);
  });

  it("shows an eviction badge when the territory is under eviction", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ under_eviction: true })}
        x={0}
        y={0}
        lens={{ kind: "stance" }}
      />,
    );
    expect(screen.getByText(/under eviction/i)).toBeInTheDocument();
  });

  it("prioritizes heat first for the heat lens", () => {
    render(
      <HexTooltip territory={makeTerritory({ heat: 0.42 })} x={0} y={0} lens={{ kind: "heat" }} />,
    );
    const stats = screen.getAllByTestId("hex-tooltip-stat-label");
    expect(stats[0]).toHaveTextContent(/heat/i);
  });

  it("prioritizes population first for a population metric lens", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ population: 5000 })}
        x={0}
        y={0}
        lens={{ kind: "metric", metric: "population" }}
      />,
    );
    const stats = screen.getAllByTestId("hex-tooltip-stat-label");
    expect(stats[0]).toHaveTextContent(/population/i);
  });
});
