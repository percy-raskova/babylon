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
import { createMapReplaySlice } from "./slices/mapReplaySlice";
import { createPanelsSlice } from "./slices/panels";
import { createUiSlice } from "./slices/uiSlice";
import { createActionsSlice } from "./slices/actionsSlice";
import { createInspectSlice } from "./slices/inspectSlice";
import { createEventsSlice } from "./slices/eventsSlice";

export const useStore = create<RootState>()((...a) => ({
  ...createSessionSlice(...a),
  ...createWorldSlice(...a),
  ...createTimeSlice(...a),
  ...createMapSlice(...a),
  ...createMapReplaySlice(...a),
  ...createPanelsSlice(...a),
  ...createUiSlice(...a),
  ...createActionsSlice(...a),
  ...createInspectSlice(...a),
  ...createEventsSlice(...a),
}));

export type { RootState } from "./types";
// Selection / InspectionFrame are deliberately NOT re-exported here: every
// consumer imports them from their slice files directly (spec-113 Lane G
// dead-export finding — orchestrator removal).
export type { TimeStatus } from "./slices/timeSlice";
export type { TakeoverKind } from "./slices/uiSlice";
export type { MapReplayStatus } from "./slices/mapReplaySlice";
export type { PanelKey, TakeoverPanelKey, InspectorKind } from "./slices/panels";
export type { Panel, PanelState } from "./slices/panels/panelFactory";
export type { PendingActionEntry } from "./slices/actionsSlice";
