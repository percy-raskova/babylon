/**
 * Map state store — manages view state, active layer, overlays,
 * and multi-scale spatial framing.
 *
 * Phase 7: lensOverride removed. LensBar is the sole layer selector.
 */

import { create } from "zustand";
import type { AdminLevel, MapLayer } from "@/types/game";
import type { LensMode } from "@/components/map/mapLensLayers";

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

  /**
   * Spec-070 political-topology lens mode (stance/heat/habitability/
   * faction/collapse). Distinct from `activeLayer` (the single-metric
   * data-ramp layer) — see spec-093 Assumptions. Independent from the
   * analytical `LensId` (economic/political/social/strategic) too.
   */
  lensMode: LensMode;
  /** Selected faction for the "faction" lens mode. */
  factionFilter: string | null;

  setActiveLayer: (layer: MapLayer) => void;
  setLayerOpacity: (opacity: number) => void;
  toggleEdges: () => void;
  /** Switch admin framing level. */
  setActiveFraming: (level: AdminLevel) => void;
  /** Update viewport bbox from DeckGL onViewStateChange. */
  setViewportBbox: (bbox: [number, number, number, number] | null) => void;
  /** Update hex resolution from map zoom. */
  setHexResolution: (resolution: number) => void;
  /** Switch the political-topology lens mode. */
  setLensMode: (mode: LensMode) => void;
  /** Select the faction shown by the "faction" lens mode. */
  setFactionFilter: (factionId: string | null) => void;
}

export const useMapStore = create<MapState>((set) => ({
  activeLayer: "heat",
  layerOpacity: 0.8,
  showEdges: false,
  activeFraming: "county",
  viewportBbox: null,
  hexResolution: 7,
  lensMode: "stance",
  factionFilter: null,

  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setLayerOpacity: (opacity) => set({ layerOpacity: opacity }),
  toggleEdges: () => set((s) => ({ showEdges: !s.showEdges })),
  setActiveFraming: (level) => set({ activeFraming: level }),
  setViewportBbox: (bbox) => set({ viewportBbox: bbox }),
  setHexResolution: (resolution) => set({ hexResolution: resolution }),
  setLensMode: (mode) => set({ lensMode: mode }),
  setFactionFilter: (factionId) => set({ factionFilter: factionId }),
}));
