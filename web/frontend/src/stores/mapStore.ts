/**
 * Map state store — manages view state, active layer, and overlays.
 */

import { create } from "zustand";
import type { MapLayer } from "@/types/game";

interface MapState {
  /** Active hex color layer. */
  activeLayer: MapLayer;
  /** Layer opacity [0, 1]. */
  layerOpacity: number;
  /** Show edge overlay lines on map. */
  showEdges: boolean;

  setActiveLayer: (layer: MapLayer) => void;
  setLayerOpacity: (opacity: number) => void;
  toggleEdges: () => void;
}

export const useMapStore = create<MapState>((set) => ({
  activeLayer: "heat",
  layerOpacity: 0.8,
  showEdges: false,

  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setLayerOpacity: (opacity) => set({ layerOpacity: opacity }),
  toggleEdges: () => set((s) => ({ showEdges: !s.showEdges })),
}));
