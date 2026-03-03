/**
 * Unit tests for the UI state Zustand store.
 */

import { describe, it, expect } from "vitest";
import { useUIStore } from "./uiStore";

describe("useUIStore", () => {
  it("has correct initial state", () => {
    const state = useUIStore.getState();
    expect(state.selectedNodeId).toBeNull();
    expect(state.selectedHexId).toBeNull();
    expect(state.hoveredNodeId).toBeNull();
    expect(state.rightPanelOpen).toBe(true);
    expect(state.bottomPanelOpen).toBe(true);
    expect(state.bottomTab).toBe("timeseries");
    expect(state.pendingVerb).toBeNull();
    expect(state.pendingOrgId).toBeNull();
    expect(state.pendingTargetId).toBeNull();
    expect(state.pendingParams).toEqual({});
  });

  it("setSelectedNode updates and clears", () => {
    useUIStore.getState().setSelectedNode("entity-1");
    expect(useUIStore.getState().selectedNodeId).toBe("entity-1");

    useUIStore.getState().setSelectedNode(null);
    expect(useUIStore.getState().selectedNodeId).toBeNull();
  });

  it("setSelectedHex updates and clears", () => {
    useUIStore.getState().setSelectedHex("territory-1");
    expect(useUIStore.getState().selectedHexId).toBe("territory-1");

    useUIStore.getState().setSelectedHex(null);
    expect(useUIStore.getState().selectedHexId).toBeNull();
  });

  it("setHoveredNode updates and clears", () => {
    useUIStore.getState().setHoveredNode("entity-1");
    expect(useUIStore.getState().hoveredNodeId).toBe("entity-1");

    useUIStore.getState().setHoveredNode(null);
    expect(useUIStore.getState().hoveredNodeId).toBeNull();
  });

  it("toggleRightPanel toggles state", () => {
    expect(useUIStore.getState().rightPanelOpen).toBe(true);
    useUIStore.getState().toggleRightPanel();
    expect(useUIStore.getState().rightPanelOpen).toBe(false);
    useUIStore.getState().toggleRightPanel();
    expect(useUIStore.getState().rightPanelOpen).toBe(true);
  });

  it("toggleBottomPanel toggles state", () => {
    expect(useUIStore.getState().bottomPanelOpen).toBe(true);
    useUIStore.getState().toggleBottomPanel();
    expect(useUIStore.getState().bottomPanelOpen).toBe(false);
    useUIStore.getState().toggleBottomPanel();
    expect(useUIStore.getState().bottomPanelOpen).toBe(true);
  });

  it("setBottomTab switches tabs", () => {
    useUIStore.getState().setBottomTab("events");
    expect(useUIStore.getState().bottomTab).toBe("events");

    useUIStore.getState().setBottomTab("graph");
    expect(useUIStore.getState().bottomTab).toBe("graph");

    useUIStore.getState().setBottomTab("timeseries");
    expect(useUIStore.getState().bottomTab).toBe("timeseries");
  });

  it("setPendingAction sets verb and org, clears target", () => {
    // Set a target first
    useUIStore.getState().setPendingTarget("target-old");
    expect(useUIStore.getState().pendingTargetId).toBe("target-old");

    useUIStore.getState().setPendingAction("educate", "org-1");
    const state = useUIStore.getState();
    expect(state.pendingVerb).toBe("educate");
    expect(state.pendingOrgId).toBe("org-1");
    expect(state.pendingTargetId).toBeNull();
    expect(state.pendingParams).toEqual({});
  });

  it("setPendingTarget updates target", () => {
    useUIStore.getState().setPendingTarget("entity-proletariat");
    expect(useUIStore.getState().pendingTargetId).toBe("entity-proletariat");

    useUIStore.getState().setPendingTarget(null);
    expect(useUIStore.getState().pendingTargetId).toBeNull();
  });

  it("clearPendingAction resets all pending state", () => {
    useUIStore.getState().setPendingAction("attack", "org-1");
    useUIStore.getState().setPendingTarget("entity-2");

    useUIStore.getState().clearPendingAction();
    const state = useUIStore.getState();
    expect(state.pendingVerb).toBeNull();
    expect(state.pendingOrgId).toBeNull();
    expect(state.pendingTargetId).toBeNull();
    expect(state.pendingParams).toEqual({});
  });
});
