/**
 * The one cockpit zustand store (spec-110 B3) — replaces the three
 * independent legacy stores (`gameStore`/`mapStore`/`uiStore`) and their
 * 13 independent 2s pollers with one sliced store plus one fetch
 * orchestrator (`./orchestrator.ts`).
 */

import { create } from "zustand";
import type { RootState } from "./types";
import { createSessionSlice } from "./slices/sessionSlice";
import { createWorldSlice } from "./slices/worldSlice";
import { createTimeSlice } from "./slices/timeSlice";
import { createMapSlice } from "./slices/mapSlice";
import { createPanelsSlice } from "./slices/panels";
import { createUiSlice } from "./slices/uiSlice";

export const useStore = create<RootState>()((...a) => ({
  ...createSessionSlice(...a),
  ...createWorldSlice(...a),
  ...createTimeSlice(...a),
  ...createMapSlice(...a),
  ...createPanelsSlice(...a),
  ...createUiSlice(...a),
}));

export type { RootState } from "./types";
export type { Selection } from "./slices/mapSlice";
export type { TimeStatus } from "./slices/timeSlice";
export type { DockTab } from "./slices/uiSlice";
export type { PanelKey, InspectorKind } from "./slices/panels";
export type { Panel, PanelState } from "./slices/panels/panelFactory";
