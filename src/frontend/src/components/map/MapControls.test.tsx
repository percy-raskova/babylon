/**
 * Unit tests for MapControls — the composed bar+legend+framing cluster
 * (spec-113 Lane B) DeckGLMap now delegates to.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MapControls } from "./MapControls";
import { DEFAULT_LENS } from "@/lib/lens";

describe("MapControls", () => {
  it("composes the lens bar, legend, and framing selector", () => {
    render(<MapControls lens={DEFAULT_LENS} framing="county" />);
    expect(screen.getByTestId("map-mode-selector")).toBeInTheDocument();
    expect(screen.getByTestId("map-legend")).toBeInTheDocument();
    expect(screen.getByTestId("framing-selector")).toBeInTheDocument();
  });

  it("renders the registry label for the active lens's legend", () => {
    render(<MapControls lens={{ kind: "heat" }} framing="county" />);
    expect(screen.getByTestId("map-legend")).toHaveTextContent(/heat/i);
  });

  it("renders no legend swatch for a lens with no registry entry (falls back to lensLegendLabel, no ramp)", () => {
    render(<MapControls lens={{ kind: "metric", metric: "occ" }} framing="county" />);
    expect(screen.queryByTestId("map-legend")).not.toBeInTheDocument();
  });

  it("renders the legendStatusText chip only when provided", () => {
    const { rerender } = render(<MapControls lens={DEFAULT_LENS} framing="county" />);
    expect(screen.queryByTestId("lens-legend-label")).not.toBeInTheDocument();

    rerender(
      <MapControls
        lens={DEFAULT_LENS}
        framing="county"
        legendStatusText="Imperial Rent — no data"
      />,
    );
    expect(screen.getByTestId("lens-legend-label")).toHaveTextContent("Imperial Rent — no data");
  });

  it("forwards availability so degraded lenses are omitted from the bar", () => {
    render(
      <MapControls
        lens={DEFAULT_LENS}
        framing="county"
        availability={{ availableMetrics: ["heat"] }}
      />,
    );
    expect(screen.queryByTestId("lens-mode-class_composition")).not.toBeInTheDocument();
  });

  it("bounds the lens cluster to the map-safe area (right-anchored + max-width capped)", () => {
    // Structural guard (spec-113 Phase V): the grouped lens bar wraps (flex-wrap),
    // so with only a right anchor and no width cap its row slid left UNDER the
    // outliner rail and the buttons stopped taking clicks (z-strata interception,
    // invisible to jsdom hit-testing). The cluster must stay right-anchored AND
    // max-width-capped to chrome/layout.ts's inter-rail safe area — remove either
    // and the overflow returns. (The live 9-lens e2e is the end-to-end guard.)
    render(<MapControls lens={DEFAULT_LENS} framing="county" />);
    const cluster = screen.getByTestId("map-mode-selector").parentElement;
    expect(cluster?.style.right, "lens cluster must be right-anchored").toBeTruthy();
    expect(
      cluster?.style.maxWidth,
      "lens cluster must be width-capped to the safe area",
    ).toBeTruthy();
  });

  describe("honest-empty ramp hint (rampEmpty)", () => {
    // Owner-picked treatment: when the active ramp lens has no usable value
    // (degenerate domain — every region identical/absent, e.g. the static
    // economy), dim the ramp, drop the marker, and add a muted note that points
    // to categorical lenses that DO have data. Constitution III.11 loud-failure.
    it("renders no hint by default", () => {
      render(<MapControls lens={DEFAULT_LENS} framing="county" />);
      expect(screen.queryByTestId("map-legend-empty-hint")).not.toBeInTheDocument();
      expect(screen.getByTestId("map-legend")).toHaveAttribute("data-muted", "false");
    });

    it("renders the note and mutes the legend when rampEmpty is set", () => {
      render(<MapControls lens={DEFAULT_LENS} framing="county" rampEmpty />);
      expect(screen.getByTestId("map-legend-empty-hint")).toHaveTextContent(/no variation/i);
      expect(screen.getByTestId("map-legend")).toHaveAttribute("data-muted", "true");
    });

    it("suggests the reliably-populated categorical lenses that availability allows", () => {
      render(
        <MapControls
          lens={DEFAULT_LENS}
          framing="county"
          rampEmpty
          availability={{ availableMetrics: ["dominant_class"] }}
        />,
      );
      expect(screen.getByTestId("empty-hint-lens-class_composition")).toBeInTheDocument();
      expect(screen.getByTestId("empty-hint-lens-stance")).toBeInTheDocument();
    });

    it("omits a suggested lens that availability degrades away (never suggests a dead lens)", () => {
      // class_composition needs the dominant_class metric; without it, only the
      // always-available stance survives — no misleading click-to-nothing.
      render(
        <MapControls
          lens={DEFAULT_LENS}
          framing="county"
          rampEmpty
          availability={{ availableMetrics: ["heat"] }}
        />,
      );
      expect(screen.queryByTestId("empty-hint-lens-class_composition")).not.toBeInTheDocument();
      expect(screen.getByTestId("empty-hint-lens-stance")).toBeInTheDocument();
    });

    it("clicking a suggested lens switches to it via onLensChange", () => {
      const onLensChange = vi.fn();
      render(
        <MapControls
          lens={DEFAULT_LENS}
          framing="county"
          rampEmpty
          onLensChange={onLensChange}
          availability={{ availableMetrics: ["dominant_class"] }}
        />,
      );
      fireEvent.click(screen.getByTestId("empty-hint-lens-stance"));
      expect(onLensChange).toHaveBeenCalledWith({ kind: "stance" });
    });
  });
});
