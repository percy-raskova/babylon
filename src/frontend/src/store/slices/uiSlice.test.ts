/**
 * Unit tests for the ui slice (spec-110 B3) — dock tabs, bottom-strip
 * collapse, focus. Pure state, no network.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";

beforeEach(() => {
  resetStore();
});

describe("ui slice", () => {
  it("defaults to the timeseries dock tab, expanded bottom strip, no focus, actions right-dock tab", () => {
    const { ui } = useStore.getState();
    expect(ui.activeDockTab).toBe("timeseries");
    expect(ui.bottomStripCollapsed).toBe(false);
    expect(ui.focusedPanelId).toBeNull();
    expect(ui.rightDockTab).toBe("actions");
  });

  it("setRightDockTab switches between actions and inspector", () => {
    useStore.getState().ui.setRightDockTab("inspector");
    expect(useStore.getState().ui.rightDockTab).toBe("inspector");
    useStore.getState().ui.setRightDockTab("actions");
    expect(useStore.getState().ui.rightDockTab).toBe("actions");
  });

  it("setActiveDockTab switches tabs", () => {
    useStore.getState().ui.setActiveDockTab("graph");
    expect(useStore.getState().ui.activeDockTab).toBe("graph");
  });

  it("toggleBottomStrip flips collapsed state", () => {
    useStore.getState().ui.toggleBottomStrip();
    expect(useStore.getState().ui.bottomStripCollapsed).toBe(true);
    useStore.getState().ui.toggleBottomStrip();
    expect(useStore.getState().ui.bottomStripCollapsed).toBe(false);
  });

  it("setFocusedPanel sets and clears focus", () => {
    useStore.getState().ui.setFocusedPanel("panel-economy");
    expect(useStore.getState().ui.focusedPanelId).toBe("panel-economy");
    useStore.getState().ui.setFocusedPanel(null);
    expect(useStore.getState().ui.focusedPanelId).toBeNull();
  });
});
