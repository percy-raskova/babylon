/**
 * Unit tests for MapModeSelector — the spec-093 lens-mode control, adapted
 * (spec-110 B2) to be a controlled component driven by the `Lens` union
 * instead of reading/writing `mapStore` directly (stores are B3 territory).
 */

import { useState } from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MapModeSelector } from "./MapModeSelector";
import type { Lens } from "@/lib/lens";

/** Wraps MapModeSelector with local state so click handlers are exercised. */
function ControlledSelector({ initial = { kind: "stance" } as Lens }: { initial?: Lens }) {
  const [lens, setLens] = useState<Lens>(initial);
  return <MapModeSelector lens={lens} onLensChange={setLens} />;
}

describe("MapModeSelector", () => {
  it("renders a button for each of the 5 lens modes", () => {
    render(<ControlledSelector />);
    for (const mode of ["stance", "heat", "habitability", "faction", "collapse"]) {
      expect(screen.getByTestId(`lens-mode-${mode}`)).toBeInTheDocument();
    }
  });

  it("marks the active lens button as pressed", () => {
    render(<ControlledSelector />);
    expect(screen.getByTestId("lens-mode-stance")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("lens-mode-heat")).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking a lens button calls onLensChange with the new kind", () => {
    render(<ControlledSelector />);
    fireEvent.click(screen.getByTestId("lens-mode-collapse"));
    expect(screen.getByTestId("lens-mode-collapse")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("lens-mode-stance")).toHaveAttribute("aria-pressed", "false");
  });

  it("cycles through all 5 lenses via clicks", () => {
    render(<ControlledSelector />);
    for (const mode of ["heat", "habitability", "faction", "collapse", "stance"]) {
      fireEvent.click(screen.getByTestId(`lens-mode-${mode}`));
      expect(screen.getByTestId(`lens-mode-${mode}`)).toHaveAttribute("aria-pressed", "true");
    }
  });

  it("a metric-kind lens is not mistaken for any mode button being pressed", () => {
    render(<ControlledSelector initial={{ kind: "metric", metric: "profit_rate" }} />);
    for (const mode of ["stance", "heat", "habitability", "faction", "collapse"]) {
      expect(screen.getByTestId(`lens-mode-${mode}`)).toHaveAttribute("aria-pressed", "false");
    }
  });

  it("shows a faction picker only when the faction lens is active and factions exist", () => {
    const { rerender } = render(
      <MapModeSelector
        lens={{ kind: "stance" }}
        onLensChange={() => {}}
        factions={[{ id: "FAC_A", colonial_stance: "uphold" }]}
      />,
    );
    expect(screen.queryByTestId("faction-filter-select")).not.toBeInTheDocument();

    rerender(
      <MapModeSelector
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
      <MapModeSelector
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
});
