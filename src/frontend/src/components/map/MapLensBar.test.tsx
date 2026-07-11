/**
 * Unit tests for MapLensBar — the registry-driven replacement for
 * MapModeSelector (spec-113 Lane B).
 */

import { useState } from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MapLensBar } from "./MapLensBar";
import { LENS_REGISTRY, DEFAULT_LENS_ID } from "@/lib/lenses/registry";
import { DEFAULT_LENS, type Lens } from "@/lib/lens";

/** Wraps MapLensBar with local state so click handlers are exercised. */
function ControlledBar({ initial = DEFAULT_LENS }: { initial?: Lens }) {
  const [lens, setLens] = useState<Lens>(initial);
  return <MapLensBar lens={lens} onLensChange={setLens} />;
}

describe("MapLensBar", () => {
  it("renders a button for every registered lens", () => {
    render(<ControlledBar />);
    for (const def of LENS_REGISTRY) {
      expect(screen.getByTestId(`lens-mode-${def.id}`)).toBeInTheDocument();
    }
  });

  it("marks the default lens's button as pressed on mount", () => {
    render(<ControlledBar />);
    expect(screen.getByTestId(`lens-mode-${DEFAULT_LENS_ID}`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("lens-mode-heat")).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking a lens button calls onLensChange with that lens's toLens() value", () => {
    render(<ControlledBar />);
    fireEvent.click(screen.getByTestId("lens-mode-collapse"));
    expect(screen.getByTestId("lens-mode-collapse")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId(`lens-mode-${DEFAULT_LENS_ID}`)).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("cycles through every registered lens via clicks", () => {
    render(<ControlledBar />);
    for (const def of LENS_REGISTRY) {
      fireEvent.click(screen.getByTestId(`lens-mode-${def.id}`));
      expect(screen.getByTestId(`lens-mode-${def.id}`)).toHaveAttribute("aria-pressed", "true");
    }
  });

  it("renders one group cluster per non-empty LENS_GROUPS entry", () => {
    render(<ControlledBar />);
    expect(screen.getByTestId("lens-group-extraction")).toBeInTheDocument();
    expect(screen.getByTestId("lens-group-struggle")).toBeInTheDocument();
    expect(screen.getByTestId("lens-group-political")).toBeInTheDocument();
    expect(screen.getByTestId("lens-group-reproduction")).toBeInTheDocument();
  });

  it("shows a faction picker only when the faction lens is active and factions exist", () => {
    const { rerender } = render(
      <MapLensBar
        lens={DEFAULT_LENS}
        onLensChange={() => {}}
        factions={[{ id: "FAC_A", colonial_stance: "uphold" }]}
      />,
    );
    expect(screen.queryByTestId("faction-filter-select")).not.toBeInTheDocument();

    rerender(
      <MapLensBar
        lens={{ kind: "faction" }}
        onLensChange={() => {}}
        factions={[{ id: "FAC_A", colonial_stance: "uphold" }]}
      />,
    );
    expect(screen.getByTestId("faction-filter-select")).toBeInTheDocument();
  });

  it("calls onFactionFilterChange when a faction is selected", () => {
    let selected: string | null = null;
    render(
      <MapLensBar
        lens={{ kind: "faction" }}
        onLensChange={() => {}}
        factions={[{ id: "FAC_A", colonial_stance: "uphold" }]}
        onFactionFilterChange={(id) => {
          selected = id;
        }}
      />,
    );
    fireEvent.change(screen.getByTestId("faction-filter-select"), { target: { value: "FAC_A" } });
    expect(selected).toBe("FAC_A");
  });

  it("degrades honestly: class_composition is absent when dominant_class isn't advertised", () => {
    render(
      <MapLensBar
        lens={DEFAULT_LENS}
        availability={{ availableMetrics: ["heat", "population"] }}
      />,
    );
    expect(screen.queryByTestId("lens-mode-class_composition")).not.toBeInTheDocument();
  });
});
