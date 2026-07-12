/**
 * Root store type — the union of every slice (spec-110 B3).
 *
 * One zustand store, sliced by domain (session/time/world/map/panels/ui)
 * per the ratified spec-110 B3/B4 architecture. Each slice file imports
 * `RootState` from here (type-only, so no runtime circularity) to type
 * its `StateCreator`.
 */

import type { SessionSlice } from "./slices/sessionSlice";
import type { WorldSlice } from "./slices/worldSlice";
import type { TimeSlice } from "./slices/timeSlice";
import type { MapSlice } from "./slices/mapSlice";
import type { PanelsSlice } from "./slices/panels";
import type { UiSlice } from "./slices/uiSlice";
import type { ActionsSlice } from "./slices/actionsSlice";
import type { InspectSlice } from "./slices/inspectSlice";
import type { EventsSlice } from "./slices/eventsSlice";

export type RootState = SessionSlice &
  WorldSlice &
  TimeSlice &
  MapSlice &
  PanelsSlice &
  UiSlice &
  ActionsSlice &
  InspectSlice &
  EventsSlice;
