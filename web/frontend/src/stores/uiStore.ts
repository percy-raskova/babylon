/**
 * UI state store — manages selection, panel visibility, and pending actions.
 */

import { create } from "zustand";
import type { PlayerVerb } from "@/types/game";

export type BottomTab = "timeseries" | "events" | "graph";

interface UIState {
  /** Currently selected node (entity/org/institution) ID. */
  selectedNodeId: string | null;
  /** Currently selected hex (territory) ID. */
  selectedHexId: string | null;
  /** Currently hovered node ID (for cross-view highlight). */
  hoveredNodeId: string | null;

  /** Right panel collapsed state. */
  rightPanelOpen: boolean;
  /** Bottom panel collapsed state. */
  bottomPanelOpen: boolean;
  /** Active bottom tab. */
  bottomTab: BottomTab;

  /** Action composition — pending turn before submission. */
  pendingVerb: PlayerVerb | null;
  pendingOrgId: string | null;
  pendingTargetId: string | null;
  pendingParams: Record<string, unknown>;

  setSelectedNode: (id: string | null) => void;
  setSelectedHex: (id: string | null) => void;
  setHoveredNode: (id: string | null) => void;
  toggleRightPanel: () => void;
  toggleBottomPanel: () => void;
  setBottomTab: (tab: BottomTab) => void;
  setPendingAction: (verb: PlayerVerb, orgId: string) => void;
  setPendingTarget: (targetId: string | null) => void;
  clearPendingAction: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  selectedNodeId: null,
  selectedHexId: null,
  hoveredNodeId: null,
  rightPanelOpen: true,
  bottomPanelOpen: true,
  bottomTab: "timeseries",
  pendingVerb: null,
  pendingOrgId: null,
  pendingTargetId: null,
  pendingParams: {},

  setSelectedNode: (id) => set({ selectedNodeId: id }),
  setSelectedHex: (id) => set({ selectedHexId: id }),
  setHoveredNode: (id) => set({ hoveredNodeId: id }),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  toggleBottomPanel: () => set((s) => ({ bottomPanelOpen: !s.bottomPanelOpen })),
  setBottomTab: (tab) => set({ bottomTab: tab }),
  setPendingAction: (verb, orgId) =>
    set({ pendingVerb: verb, pendingOrgId: orgId, pendingTargetId: null, pendingParams: {} }),
  setPendingTarget: (targetId) => set({ pendingTargetId: targetId }),
  clearPendingAction: () =>
    set({ pendingVerb: null, pendingOrgId: null, pendingTargetId: null, pendingParams: {} }),
}));
