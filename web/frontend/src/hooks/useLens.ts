/**
 * useLens — coordinates lens switching across stores.
 *
 * Per data-model.md Lens State Machine: switching a lens updates uiStore.activeLens,
 * sets mapStore.activeLayer to the lens's primaryLayer (unless user has manually
 * overridden the layer), and clears the lensOverride flag on explicit lens switch.
 */

import { useCallback } from "react";
import { useUIStore } from "@/stores/uiStore";
import { useMapStore } from "@/stores/mapStore";
import { getLensById } from "@/lib/lensDefinitions";
import type { LensId } from "@/types/game";

interface UseLensReturn {
  activeLens: LensId;
  switchLens: (lensId: LensId) => void;
}

/**
 * Hook for lens navigation. Returns the active lens ID and a function to
 * switch lenses, coordinating updates across uiStore and mapStore.
 */
export function useLens(): UseLensReturn {
  const activeLens = useUIStore((s) => s.activeLens);

  const switchLens = useCallback((lensId: LensId) => {
    const lens = getLensById(lensId);

    // Update active lens in UI store
    useUIStore.getState().setActiveLens(lensId);

    // Clear lens override and set the lens's primary layer
    useMapStore.getState().clearLensOverride();
    useMapStore.setState({ activeLayer: lens.primaryLayer });
  }, []);

  return { activeLens, switchLens };
}
