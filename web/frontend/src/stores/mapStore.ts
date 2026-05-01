/**
 * Map state store — manages view state, active layer, overlays,
 * and multi-scale spatial framing.
 *
 * Phase 7: lensOverride removed. LensBar is the sole layer selector.
 */

import { create } from "zustand";
import type { AdminLevel, MapLayer } from "@/types/game";

interface MapState {
  /** Active hex color layer. */
  activeLayer: MapLayer;
  /** Layer opacity [0, 1]. */
  layerOpacity: number;
  /** Show edge overlay lines on map. */
  showEdges: boolean;

  /** Active administrative framing level for aggregation. */
  activeFraming: AdminLevel;
  /** Current viewport bounding box [minLng, minLat, maxLng, maxLat]. */
  viewportBbox: [number, number, number, number] | null;
  /** Current H3 resolution derived from map zoom (not user-settable). */
  hexResolution: number;

  setActiveLayer: (layer: MapLayer) => void;
  setLayerOpacity: (opacity: number) => void;
  toggleEdges: () => void;
  /** Switch admin framing level. */
  setActiveFraming: (level: AdminLevel) => void;
  /** Update viewport bbox from DeckGL onViewStateChange. */
  setViewportBbox: (bbox: [number, number, number, number] | null) => void;
  /** Update hex resolution from map zoom. */
  setHexResolution: (resolution: number) => void;
}

export const useMapStore = create<MapState>((set) => ({
  activeLayer: "heat",
  layerOpacity: 0.8,
  showEdges: false,
  activeFraming: "county",
  viewportBbox: null,
  hexResolution: 7,

  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setLayerOpacity: (opacity) => set({ layerOpacity: opacity }),
  toggleEdges: () => set((s) => ({ showEdges: !s.showEdges })),
  setActiveFraming: (level) => set({ activeFraming: level }),
  setViewportBbox: (bbox) => set({ viewportBbox: bbox }),
  setHexResolution: (resolution) => set({ hexResolution: resolution }),
}));
