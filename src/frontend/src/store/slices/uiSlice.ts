/**
 * UI slice — dock tabs, bottom-strip collapse, focus, takeover overlays
 * (spec-110 B3, takeover field added spec-110 B5).
 *
 * Deliberately narrow: this is chrome state only. Panel data/loading/error
 * lives in `panels/*`; selection/viewport lives in `mapSlice`.
 */

import type { StateCreator } from "zustand";
import type { RootState } from "../types";

/** Mirrors the legacy `BottomTab` union (`web/frontend/src/stores/uiStore.ts`). */
export type DockTab = "timeseries" | "events" | "graph" | "notifications";

/** The three Right Dock tabs (spec-110 B3 stage 2 + B5 Objectives). */
export type RightDockTab = "actions" | "inspector" | "objectives";

/** The three full-screen takeover surfaces (spec-110 B5), or none open. */
export type TakeoverKind = "wire" | "chronicle" | "dialectic";

export interface UiSlice {
  ui: {
    activeDockTab: DockTab;
    bottomStripCollapsed: boolean;
    /** Id of whichever docked panel currently has keyboard/visual focus. */
    focusedPanelId: string | null;
    /** Which of the Right Dock's three tabs is showing. */
    rightDockTab: RightDockTab;
    /** Which takeover overlay is open, if any — the map stays mounted underneath. */
    takeover: { active: TakeoverKind | null };

    setActiveDockTab: (tab: DockTab) => void;
    toggleBottomStrip: () => void;
    setFocusedPanel: (id: string | null) => void;
    setRightDockTab: (tab: RightDockTab) => void;
    openTakeover: (kind: TakeoverKind) => void;
    closeTakeover: () => void;
  };
}

export const createUiSlice: StateCreator<RootState, [], [], UiSlice> = (set) => ({
  ui: {
    activeDockTab: "timeseries",
    bottomStripCollapsed: false,
    focusedPanelId: null,
    rightDockTab: "actions",
    takeover: { active: null },

    setActiveDockTab: (tab) => set((s) => ({ ui: { ...s.ui, activeDockTab: tab } })),
    toggleBottomStrip: () =>
      set((s) => ({ ui: { ...s.ui, bottomStripCollapsed: !s.ui.bottomStripCollapsed } })),
    setFocusedPanel: (id) => set((s) => ({ ui: { ...s.ui, focusedPanelId: id } })),
    setRightDockTab: (tab) => set((s) => ({ ui: { ...s.ui, rightDockTab: tab } })),
    openTakeover: (kind) => set((s) => ({ ui: { ...s.ui, takeover: { active: kind } } })),
    closeTakeover: () => set((s) => ({ ui: { ...s.ui, takeover: { active: null } } })),
  },
});
