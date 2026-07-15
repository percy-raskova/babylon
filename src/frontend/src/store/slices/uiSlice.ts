/**
 * UI slice — chrome panel visibility, focus, takeover overlays (spec-110
 * B3, takeover field added spec-110 B5; `ui.chrome` added spec-113 Lane A,
 * architecture.md §1.4).
 *
 * Deliberately narrow: this is chrome state only. Panel data/loading/error
 * lives in `panels/*`; selection/viewport lives in `mapSlice`.
 *
 * `activeDockTab`/`bottomStripCollapsed`/`rightDockTab` (the RightDock/
 * BottomStrip tab-and-collapse state) are RETIRED — `RightDock.tsx` and
 * `BottomStrip.tsx` are deleted (architecture §1.2's "disperse" row); the
 * `DockTab`/`RightDockTab` alias names were dropped from `store/index.ts`
 * in the same sweep once their last consumers went.
 */

import type { StateCreator } from "zustand";
import type { RootState } from "../types";

/** The three full-screen takeover surfaces (spec-110 B5), or none open. */
export type TakeoverKind = "wire" | "chronicle" | "dialectic";

/** `BottomDrawer`'s four states (architecture §1.4): closed, or one of its three contents. */
export type BottomDrawerState = "none" | "trends" | "events" | "economy";

/**
 * Chrome panel open/collapsed state (architecture §1.4). One field per
 * floating chrome panel that has a show/hide affordance; `composerOpen`
 * gates `ActionDock`'s `FloatingPanel` housing `ActionComposer`.
 */
export interface ChromeState {
  outlinerOpen: boolean;
  eventTrayOpen: boolean;
  objectivesOpen: boolean;
  /** The Bifurcation gauge HUD widget (Wave 3 R2a) — same collapse/expand
   *  affordance as `objectivesOpen`, no keyboard hotkey (none of this
   *  family has one; `useSpeedShortcut`'s number keys are unrelated). */
  bifurcationOpen: boolean;
  bottomDrawer: BottomDrawerState;
  composerOpen: boolean;
}

export interface UiSlice {
  ui: {
    chrome: ChromeState;
    /** Id of whichever docked panel currently has keyboard/visual focus. */
    focusedPanelId: string | null;
    /** Which takeover overlay is open, if any — the map stays mounted underneath. */
    takeover: { active: TakeoverKind | null };

    toggleOutliner: () => void;
    toggleEventTray: () => void;
    toggleObjectives: () => void;
    toggleBifurcation: () => void;
    toggleComposer: () => void;
    setBottomDrawer: (state: BottomDrawerState) => void;
    setFocusedPanel: (id: string | null) => void;
    openTakeover: (kind: TakeoverKind) => void;
    closeTakeover: () => void;
  };
}

export const createUiSlice: StateCreator<RootState, [], [], UiSlice> = (set) => ({
  ui: {
    chrome: {
      outlinerOpen: true,
      eventTrayOpen: true,
      objectivesOpen: true,
      bifurcationOpen: true,
      bottomDrawer: "trends",
      composerOpen: true,
    },
    focusedPanelId: null,
    takeover: { active: null },

    toggleOutliner: () =>
      set((s) => ({
        ui: { ...s.ui, chrome: { ...s.ui.chrome, outlinerOpen: !s.ui.chrome.outlinerOpen } },
      })),
    toggleEventTray: () =>
      set((s) => ({
        ui: { ...s.ui, chrome: { ...s.ui.chrome, eventTrayOpen: !s.ui.chrome.eventTrayOpen } },
      })),
    toggleObjectives: () =>
      set((s) => ({
        ui: { ...s.ui, chrome: { ...s.ui.chrome, objectivesOpen: !s.ui.chrome.objectivesOpen } },
      })),
    toggleBifurcation: () =>
      set((s) => ({
        ui: { ...s.ui, chrome: { ...s.ui.chrome, bifurcationOpen: !s.ui.chrome.bifurcationOpen } },
      })),
    toggleComposer: () =>
      set((s) => ({
        ui: { ...s.ui, chrome: { ...s.ui.chrome, composerOpen: !s.ui.chrome.composerOpen } },
      })),
    setBottomDrawer: (state) =>
      set((s) => ({ ui: { ...s.ui, chrome: { ...s.ui.chrome, bottomDrawer: state } } })),
    setFocusedPanel: (id) => set((s) => ({ ui: { ...s.ui, focusedPanelId: id } })),
    openTakeover: (kind) => set((s) => ({ ui: { ...s.ui, takeover: { active: kind } } })),
    closeTakeover: () => set((s) => ({ ui: { ...s.ui, takeover: { active: null } } })),
  },
});
