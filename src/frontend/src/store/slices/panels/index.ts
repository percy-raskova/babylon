/**
 * Panels slice — one docked-panel state per endpoint (spec-110 B3).
 *
 * `summary`/`timeseries`/`economy`/`communities`/`map` are the 5 tick-driven
 * panels the fetch orchestrator fans out to on `onTickAdvanced`. `inspector`
 * is selection-driven (see `mapSlice.setSelection`), not tick-driven, so it
 * is deliberately excluded from `PANEL_KEYS`.
 */

import type { StateCreator } from "zustand";
import type {
  GameSummaryPayload,
  TimeseriesPayload,
  EconomyDashboardPayload,
  CommunitiesDashboardPayload,
} from "@/types/game";
import type { FeatureCollection } from "geojson";
import type { RootState } from "../../types";
import { createPanel, type Panel } from "./panelFactory";
import { createInspectorPanel, type InspectorPanel } from "./inspectorPanel";

export type { PanelKey } from "./panelFactory";
export { PANEL_KEYS } from "./panelFactory";
export type { InspectorKind } from "./inspectorPanel";

export interface PanelsSlice {
  panels: {
    summary: Panel<GameSummaryPayload>;
    timeseries: Panel<TimeseriesPayload>;
    economy: Panel<EconomyDashboardPayload>;
    communities: Panel<CommunitiesDashboardPayload>;
    map: Panel<FeatureCollection>;
    inspector: InspectorPanel;
  };
}

export const createPanelsSlice: StateCreator<RootState, [], [], PanelsSlice> = (set, get) => {
  const summary = createPanel<GameSummaryPayload>(
    (gameId) => `/api/games/${gameId}/summary/`,
    (updater) => set((s) => ({ panels: { ...s.panels, summary: updater(s.panels.summary) } })),
    get,
  );
  const timeseries = createPanel<TimeseriesPayload>(
    (gameId) => `/api/games/${gameId}/timeseries/`,
    (updater) =>
      set((s) => ({ panels: { ...s.panels, timeseries: updater(s.panels.timeseries) } })),
    get,
  );
  const economy = createPanel<EconomyDashboardPayload>(
    (gameId) => `/api/games/${gameId}/economy/`,
    (updater) => set((s) => ({ panels: { ...s.panels, economy: updater(s.panels.economy) } })),
    get,
  );
  const communities = createPanel<CommunitiesDashboardPayload>(
    (gameId) => `/api/games/${gameId}/communities/`,
    (updater) =>
      set((s) => ({ panels: { ...s.panels, communities: updater(s.panels.communities) } })),
    get,
  );
  const mapPanel = createPanel<FeatureCollection>(
    (gameId, getRoot) => `/api/games/${gameId}/map/?zoom=${getRoot().map.framing}`,
    (updater) => set((s) => ({ panels: { ...s.panels, map: updater(s.panels.map) } })),
    get,
  );
  const inspector = createInspectorPanel((updater) =>
    set((s) => ({ panels: { ...s.panels, inspector: updater(s.panels.inspector) } })),
  );

  return { panels: { summary, timeseries, economy, communities, map: mapPanel, inspector } };
};
