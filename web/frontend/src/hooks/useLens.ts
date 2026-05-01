/**
 * useLens — coordinates lens switching across stores.
 *
 * Switching a lens updates uiStore.activeLens and mapStore.activeLayer
 * to the lens's primaryLayer. LensBar is the sole control surface.
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

    // Set the lens's primary layer
    useMapStore.setState({ activeLayer: lens.primaryLayer });
  }, []);

  return { activeLens, switchLens };
}
