/**
 * Unit tests for the map state Zustand store.
 */

import { describe, it, expect } from "vitest";
import { useMapStore } from "./mapStore";

describe("useMapStore", () => {
  it("has correct initial state", () => {
    const state = useMapStore.getState();
    expect(state.activeLayer).toBe("heat");
    expect(state.layerOpacity).toBe(0.8);
    expect(state.showEdges).toBe(false);
  });

  it("setActiveLayer switches layer", () => {
    useMapStore.getState().setActiveLayer("consciousness");
    expect(useMapStore.getState().activeLayer).toBe("consciousness");

    useMapStore.getState().setActiveLayer("wealth");
    expect(useMapStore.getState().activeLayer).toBe("wealth");

    useMapStore.getState().setActiveLayer("rent");
    expect(useMapStore.getState().activeLayer).toBe("rent");

    useMapStore.getState().setActiveLayer("biocapacity");
    expect(useMapStore.getState().activeLayer).toBe("biocapacity");

    useMapStore.getState().setActiveLayer("population");
    expect(useMapStore.getState().activeLayer).toBe("population");
  });

  it("setLayerOpacity updates value", () => {
    useMapStore.getState().setLayerOpacity(0.5);
    expect(useMapStore.getState().layerOpacity).toBe(0.5);

    useMapStore.getState().setLayerOpacity(1.0);
    expect(useMapStore.getState().layerOpacity).toBe(1.0);
  });

  it("toggleEdges toggles state", () => {
    expect(useMapStore.getState().showEdges).toBe(false);
    useMapStore.getState().toggleEdges();
    expect(useMapStore.getState().showEdges).toBe(true);
    useMapStore.getState().toggleEdges();
    expect(useMapStore.getState().showEdges).toBe(false);
  });

  it("defaults lensMode to stance with no faction filter (spec-093)", () => {
    const state = useMapStore.getState();
    expect(state.lensMode).toBe("stance");
    expect(state.factionFilter).toBeNull();
  });

  it("setLensMode cycles through all 5 political-topology lenses (spec-093)", () => {
    const lenses = ["stance", "heat", "habitability", "faction", "collapse"] as const;
    for (const lens of lenses) {
      useMapStore.getState().setLensMode(lens);
      expect(useMapStore.getState().lensMode).toBe(lens);
    }
  });

  it("setFactionFilter selects and clears a faction (spec-093)", () => {
    useMapStore.getState().setFactionFilter("FAC_A");
    expect(useMapStore.getState().factionFilter).toBe("FAC_A");

    useMapStore.getState().setFactionFilter(null);
    expect(useMapStore.getState().factionFilter).toBeNull();
  });
});
