/**
 * Panels slice — one docked-panel state per endpoint (spec-110 B3).
 *
 * `summary`/`timeseries`/`economy`/`communities`/`map` are the 5 tick-driven
 * panels the fetch orchestrator fans out to on `onTickAdvanced`. `inspector`
 * is selection-driven (see `mapSlice.setSelection`), not tick-driven, so it
 * is deliberately excluded from `PANEL_KEYS`.
 *
 * `wire`/`contradiction`/`endgame`/`objectives`/`tradeFlows` back the
 * takeover surfaces + Objectives dock tab (spec-110 B5) — same
 * fetch/loading/error/mounted shape, fanned out separately via
 * `TAKEOVER_PANEL_KEYS` since they mount on takeover-open, not shell-mount.
 */

import type { StateCreator } from "zustand";
import type {
  GameSummaryPayload,
  TimeseriesPayload,
  EconomyDashboardPayload,
  CommunitiesDashboardPayload,
} from "@/types/game";
import type { FeatureCollection } from "geojson";
import type { WireFeed } from "@/types/wire";
import type { ContradictionSnapshot, EndgameState, ObjectivesTracker } from "@/types/dialectic";
import type { TradeFlowsPayload } from "@/types/trade";
import type { RootState } from "../../types";
import { createPanel, type Panel } from "./panelFactory";
import { createInspectorPanel, type InspectorPanel } from "./inspectorPanel";

export type { PanelKey, TakeoverPanelKey } from "./panelFactory";
export { PANEL_KEYS, TAKEOVER_PANEL_KEYS } from "./panelFactory";
export type { InspectorKind } from "./inspectorPanel";

export interface PanelsSlice {
  panels: {
    summary: Panel<GameSummaryPayload>;
    timeseries: Panel<TimeseriesPayload>;
    economy: Panel<EconomyDashboardPayload>;
    communities: Panel<CommunitiesDashboardPayload>;
    map: Panel<FeatureCollection>;
    inspector: InspectorPanel;
    wire: Panel<WireFeed>;
    contradiction: Panel<ContradictionSnapshot>;
    endgame: Panel<EndgameState>;
    objectives: Panel<ObjectivesTracker>;
    tradeFlows: Panel<TradeFlowsPayload>;
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

  const wire = createPanel<WireFeed>(
    (gameId) => `/api/games/${gameId}/wire/`,
    (updater) => set((s) => ({ panels: { ...s.panels, wire: updater(s.panels.wire) } })),
    get,
  );
  const contradiction = createPanel<ContradictionSnapshot>(
    (gameId) => `/api/games/${gameId}/contradiction/`,
    (updater) =>
      set((s) => ({ panels: { ...s.panels, contradiction: updater(s.panels.contradiction) } })),
    get,
  );
  const endgame = createPanel<EndgameState>(
    (gameId) => `/api/games/${gameId}/endgame/`,
    (updater) => set((s) => ({ panels: { ...s.panels, endgame: updater(s.panels.endgame) } })),
    get,
  );
  const objectives = createPanel<ObjectivesTracker>(
    (gameId) => `/api/games/${gameId}/objectives/`,
    (updater) =>
      set((s) => ({ panels: { ...s.panels, objectives: updater(s.panels.objectives) } })),
    get,
  );
  const tradeFlows = createPanel<TradeFlowsPayload>(
    (gameId) => `/api/games/${gameId}/trade-flows/`,
    (updater) =>
      set((s) => ({ panels: { ...s.panels, tradeFlows: updater(s.panels.tradeFlows) } })),
    get,
  );

  return {
    panels: {
      summary,
      timeseries,
      economy,
      communities,
      map: mapPanel,
      inspector,
      wire,
      contradiction,
      endgame,
      objectives,
      tradeFlows,
    },
  };
};
