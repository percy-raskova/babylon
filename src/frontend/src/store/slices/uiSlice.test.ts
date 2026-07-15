/**
 * Unit tests for the ui slice (spec-113 Lane A) — chrome panel visibility,
 * focus, takeover overlays. Pure state, no network.
 *
 * `activeDockTab`/`bottomStripCollapsed`/`rightDockTab` were retired with
 * `RightDock`/`BottomStrip` (architecture.md §1.4 "subtractive" step) —
 * their behavior is now covered by `ui.chrome`'s tests below.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";

beforeEach(() => {
  resetStore();
});

describe("ui slice", () => {
  it("defaults: outliner/eventTray/objectives/bifurcation open, bottom drawer 'trends', composer open, no focus, no takeover", () => {
    const { ui } = useStore.getState();
    expect(ui.chrome.outlinerOpen).toBe(true);
    expect(ui.chrome.eventTrayOpen).toBe(true);
    expect(ui.chrome.objectivesOpen).toBe(true);
    expect(ui.chrome.bifurcationOpen).toBe(true);
    expect(ui.chrome.bottomDrawer).toBe("trends");
    expect(ui.chrome.composerOpen).toBe(true);
    expect(ui.focusedPanelId).toBeNull();
    expect(ui.takeover.active).toBeNull();
  });

  it("toggleOutliner flips outlinerOpen", () => {
    useStore.getState().ui.toggleOutliner();
    expect(useStore.getState().ui.chrome.outlinerOpen).toBe(false);
    useStore.getState().ui.toggleOutliner();
    expect(useStore.getState().ui.chrome.outlinerOpen).toBe(true);
  });

  it("toggleEventTray flips eventTrayOpen", () => {
    useStore.getState().ui.toggleEventTray();
    expect(useStore.getState().ui.chrome.eventTrayOpen).toBe(false);
    useStore.getState().ui.toggleEventTray();
    expect(useStore.getState().ui.chrome.eventTrayOpen).toBe(true);
  });

  it("toggleObjectives flips objectivesOpen", () => {
    useStore.getState().ui.toggleObjectives();
    expect(useStore.getState().ui.chrome.objectivesOpen).toBe(false);
    useStore.getState().ui.toggleObjectives();
    expect(useStore.getState().ui.chrome.objectivesOpen).toBe(true);
  });

  it("toggleBifurcation flips bifurcationOpen", () => {
    useStore.getState().ui.toggleBifurcation();
    expect(useStore.getState().ui.chrome.bifurcationOpen).toBe(false);
    useStore.getState().ui.toggleBifurcation();
    expect(useStore.getState().ui.chrome.bifurcationOpen).toBe(true);
  });

  it("toggleComposer flips composerOpen", () => {
    useStore.getState().ui.toggleComposer();
    expect(useStore.getState().ui.chrome.composerOpen).toBe(false);
    useStore.getState().ui.toggleComposer();
    expect(useStore.getState().ui.chrome.composerOpen).toBe(true);
  });

  it("setBottomDrawer switches between none/trends/events/economy", () => {
    useStore.getState().ui.setBottomDrawer("events");
    expect(useStore.getState().ui.chrome.bottomDrawer).toBe("events");
    useStore.getState().ui.setBottomDrawer("economy");
    expect(useStore.getState().ui.chrome.bottomDrawer).toBe("economy");
    useStore.getState().ui.setBottomDrawer("none");
    expect(useStore.getState().ui.chrome.bottomDrawer).toBe("none");
    useStore.getState().ui.setBottomDrawer("trends");
    expect(useStore.getState().ui.chrome.bottomDrawer).toBe("trends");
  });

  it("setFocusedPanel sets and clears focus", () => {
    useStore.getState().ui.setFocusedPanel("panel-economy");
    expect(useStore.getState().ui.focusedPanelId).toBe("panel-economy");
    useStore.getState().ui.setFocusedPanel(null);
    expect(useStore.getState().ui.focusedPanelId).toBeNull();
  });

  it("openTakeover/closeTakeover set and clear the active takeover", () => {
    useStore.getState().ui.openTakeover("wire");
    expect(useStore.getState().ui.takeover.active).toBe("wire");
    useStore.getState().ui.openTakeover("chronicle");
    expect(useStore.getState().ui.takeover.active).toBe("chronicle");
    useStore.getState().ui.openTakeover("dialectic");
    expect(useStore.getState().ui.takeover.active).toBe("dialectic");
    useStore.getState().ui.closeTakeover();
    expect(useStore.getState().ui.takeover.active).toBeNull();
  });
});
