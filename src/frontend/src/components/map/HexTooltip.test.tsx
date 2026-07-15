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

  it("prioritizes receptivity first for the mass_receptivity metric lens (Wave 5)", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ mass_receptivity: 0.56, vision_state: "mud" })}
        x={0}
        y={0}
        lens={{ kind: "metric", metric: "mass_receptivity" }}
      />,
    );
    const stats = screen.getAllByTestId("hex-tooltip-stat-label");
    expect(stats[0]).toHaveTextContent(/receptivity/i);
    expect(screen.getByText("0.56")).toBeInTheDocument();
  });

  it("prioritizes vision first for the vision_state lens, rendering the real state string (Wave 5)", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ mass_receptivity: 0.06, vision_state: "desert" })}
        x={0}
        y={0}
        lens={{ kind: "vision_state" }}
      />,
    );
    const stats = screen.getAllByTestId("hex-tooltip-stat-label");
    expect(stats[0]).toHaveTextContent(/vision/i);
    expect(screen.getByText("desert")).toBeInTheDocument();
  });

  it("renders an honest em-dash for absent receptivity values, never a fabricated 0 (Constitution III.11)", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ mass_receptivity: null, vision_state: null })}
        x={0}
        y={0}
        lens={{ kind: "vision_state" }}
      />,
    );
    const values = screen.getAllByText("—");
    expect(values.length).toBeGreaterThan(0);
  });

  it("prioritizes wage pressure first for the wage_pressure metric lens (Feature 021)", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ wage_pressure: 0.35, dispossession_intensity: 0.2 })}
        x={0}
        y={0}
        lens={{ kind: "metric", metric: "wage_pressure" }}
      />,
    );
    const stats = screen.getAllByTestId("hex-tooltip-stat-label");
    expect(stats[0]).toHaveTextContent(/wage pressure/i);
    expect(screen.getByText("0.35")).toBeInTheDocument();
  });

  it("prioritizes dispossession first for the dispossession_intensity metric lens (Feature 021)", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ wage_pressure: 0.1, dispossession_intensity: 0.62 })}
        x={0}
        y={0}
        lens={{ kind: "metric", metric: "dispossession_intensity" }}
      />,
    );
    const stats = screen.getAllByTestId("hex-tooltip-stat-label");
    expect(stats[0]).toHaveTextContent(/dispossession/i);
    expect(screen.getByText("0.62")).toBeInTheDocument();
  });

  it("renders an honest em-dash for absent wage_pressure/dispossession_intensity values, never a fabricated 0 (Constitution III.11)", () => {
    render(
      <HexTooltip
        territory={makeTerritory({ wage_pressure: null, dispossession_intensity: null })}
        x={0}
        y={0}
        lens={{ kind: "metric", metric: "wage_pressure" }}
      />,
    );
    const values = screen.getAllByText("—");
    expect(values.length).toBeGreaterThan(0);
  });
});
