/**
 * Unit tests for MapModeSelector — the spec-093 lens-mode control.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MapModeSelector } from "./MapModeSelector";
import { useMapStore } from "@/stores/mapStore";

describe("MapModeSelector", () => {
  beforeEach(() => {
    useMapStore.getState().setLensMode("stance");
  });

  it("renders a button for each of the 5 lens modes", () => {
    render(<MapModeSelector />);
    for (const mode of ["stance", "heat", "habitability", "faction", "collapse"]) {
      expect(screen.getByTestId(`lens-mode-${mode}`)).toBeInTheDocument();
    }
  });

  it("marks the active lens button as pressed", () => {
    render(<MapModeSelector />);
    expect(screen.getByTestId("lens-mode-stance")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("lens-mode-heat")).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking a lens button switches the store's lensMode", () => {
    render(<MapModeSelector />);
    fireEvent.click(screen.getByTestId("lens-mode-collapse"));
    expect(useMapStore.getState().lensMode).toBe("collapse");
  });

  it("cycles through all 5 lenses via clicks", () => {
    render(<MapModeSelector />);
    for (const mode of ["heat", "habitability", "faction", "collapse", "stance"]) {
      fireEvent.click(screen.getByTestId(`lens-mode-${mode}`));
      expect(useMapStore.getState().lensMode).toBe(mode);
    }
  });
});
