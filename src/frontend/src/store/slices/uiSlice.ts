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

/** The full-screen takeover surfaces (spec-110 B5; `network` added AW4-R2;
 *  `doctrine` added Epoch 3 Wave 6 Phase 0), or none open. */
export type TakeoverKind = "wire" | "chronicle" | "dialectic" | "network" | "doctrine";

/** `BottomDrawer`'s six states (architecture §1.4): closed, or one of its five contents. */
export type BottomDrawerState =
  "none" | "trends" | "events" | "economy" | "state-apparatus" | "edges";

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
  /** The CRISIS TIMELINE HUD widget (business-cycle phase strip) — same
   *  collapse/expand affordance as `bifurcationOpen`, no keyboard hotkey. */
  crisisTimelineOpen: boolean;
  /** The RADAR LOOP tick-scrubber HUD widget (Program 17 Wave 3,
   *  Frontend-W3R3) — same collapse/expand affordance as `bifurcationOpen`,
   *  no keyboard hotkey. */
  radarLoopOpen: boolean;
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
    toggleCrisisTimeline: () => void;
    toggleRadarLoop: () => void;
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
      crisisTimelineOpen: true,
      radarLoopOpen: true,
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
    toggleCrisisTimeline: () =>
      set((s) => ({
        ui: {
          ...s.ui,
          chrome: { ...s.ui.chrome, crisisTimelineOpen: !s.ui.chrome.crisisTimelineOpen },
        },
      })),
    toggleRadarLoop: () =>
      set((s) => ({
        ui: { ...s.ui, chrome: { ...s.ui.chrome, radarLoopOpen: !s.ui.chrome.radarLoopOpen } },
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
