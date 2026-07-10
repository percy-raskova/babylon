/**
 * UI slice — dock tabs, bottom-strip collapse, focus (spec-110 B3).
 *
 * Deliberately narrow: this is chrome state only. Panel data/loading/error
 * lives in `panels/*`; selection/viewport lives in `mapSlice`.
 */

import type { StateCreator } from "zustand";
import type { RootState } from "../types";

/** Mirrors the legacy `BottomTab` union (`web/frontend/src/stores/uiStore.ts`). */
export type DockTab = "timeseries" | "events" | "graph" | "notifications";

export interface UiSlice {
  ui: {
    activeDockTab: DockTab;
    bottomStripCollapsed: boolean;
    /** Id of whichever docked panel currently has keyboard/visual focus. */
    focusedPanelId: string | null;

    setActiveDockTab: (tab: DockTab) => void;
    toggleBottomStrip: () => void;
    setFocusedPanel: (id: string | null) => void;
  };
}

export const createUiSlice: StateCreator<RootState, [], [], UiSlice> = (set) => ({
  ui: {
    activeDockTab: "timeseries",
    bottomStripCollapsed: false,
    focusedPanelId: null,

    setActiveDockTab: (tab) => set((s) => ({ ui: { ...s.ui, activeDockTab: tab } })),
    toggleBottomStrip: () =>
      set((s) => ({ ui: { ...s.ui, bottomStripCollapsed: !s.ui.bottomStripCollapsed } })),
    setFocusedPanel: (id) => set((s) => ({ ui: { ...s.ui, focusedPanelId: id } })),
  },
});
