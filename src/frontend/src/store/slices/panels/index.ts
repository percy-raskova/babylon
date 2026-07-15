/**
 * Panels slice — one docked-panel state per endpoint (spec-110 B3).
 *
 * `summary`/`timeseries`/`economy`/`communities`/`map`/`edges`/
 * `stateApparatus` are the 7 tick-driven panels the fetch orchestrator fans
 * out to on `onTickAdvanced`.
 *
 * `wire`/`contradiction`/`endgame`/`objectives`/`tradeFlows` back the
 * takeover surfaces + Objectives dock tab (spec-110 B5) — same
 * fetch/loading/error/mounted shape, fanned out separately via
 * `TAKEOVER_PANEL_KEYS` since they mount on takeover-open, not shell-mount.
 *
 * `inspector` (the selection-driven `InspectorPanel` fetch) is RETIRED
 * (spec-113 Lane C) — `store/slices/inspectSlice.ts` now owns
 * selection-driven fetch/loading/error via `mapSlice.setSelection`'s
 * `inspect.clear()+push()` fan-out.
 */

import type { StateCreator } from "zustand";
import type {
  GameSummaryPayload,
  TimeseriesPayload,
  EconomyDashboardPayload,
  CommunitiesDashboardPayload,
  StateApparatusDashboard,
  EdgesDashboardPayload,
  OrgNetworkPayload,
} from "@/types/game";
import type { FeatureCollection } from "geojson";
import type { WireFeed } from "@/types/wire";
import type { ContradictionSnapshot, EndgameState, ObjectivesTracker } from "@/types/dialectic";
import type { TradeFlowsPayload } from "@/types/trade";
import { endpoints } from "@/api/endpoints";
import type { RootState } from "../../types";
import { createPanel, type Panel } from "./panelFactory";
import { createNarrationPanel, type NarrationPanel } from "./narrationPanel";

export type { PanelKey, TakeoverPanelKey } from "./panelFactory";
export { PANEL_KEYS, TAKEOVER_PANEL_KEYS } from "./panelFactory";
// Re-exported from mapSlice (not the deleted inspectorPanel.ts) so
// `store/index.ts`'s `export type { ... InspectorKind } from
// "./slices/panels"` line keeps working with zero edits to that
// off-limits file (spec-113 Lane C).
export type { InspectorKind } from "../mapSlice";

export interface PanelsSlice {
  panels: {
    summary: Panel<GameSummaryPayload>;
    timeseries: Panel<TimeseriesPayload>;
    economy: Panel<EconomyDashboardPayload>;
    communities: Panel<CommunitiesDashboardPayload>;
    map: Panel<FeatureCollection>;
    edges: Panel<EdgesDashboardPayload>;
    stateApparatus: Panel<StateApparatusDashboard>;
    wire: Panel<WireFeed>;
    contradiction: Panel<ContradictionSnapshot>;
    endgame: Panel<EndgameState>;
    objectives: Panel<ObjectivesTracker>;
    tradeFlows: Panel<TradeFlowsPayload>;
    narration: NarrationPanel;
    /** AW4-R2 — the Network takeover's org-network graph. */
    network: Panel<OrgNetworkPayload>;
  };
}

export const createPanelsSlice: StateCreator<RootState, [], [], PanelsSlice> = (set, get) => {
  const summary = createPanel<GameSummaryPayload>(
    (gameId) => endpoints.summary.path({ id: gameId }),
    (updater) => set((s) => ({ panels: { ...s.panels, summary: updater(s.panels.summary) } })),
    get,
  );
  const timeseries = createPanel<TimeseriesPayload>(
    (gameId) => endpoints.timeseries.path({ id: gameId }),
    (updater) =>
      set((s) => ({ panels: { ...s.panels, timeseries: updater(s.panels.timeseries) } })),
    get,
  );
  const economy = createPanel<EconomyDashboardPayload>(
    (gameId) => endpoints.economy.path({ id: gameId }),
    (updater) => set((s) => ({ panels: { ...s.panels, economy: updater(s.panels.economy) } })),
    get,
  );
  const communities = createPanel<CommunitiesDashboardPayload>(
    (gameId) => endpoints.communities.path({ id: gameId }),
    (updater) =>
      set((s) => ({ panels: { ...s.panels, communities: updater(s.panels.communities) } })),
    get,
  );
  const mapPanel = createPanel<FeatureCollection>(
    (gameId, getRoot) => `${endpoints.map.path({ id: gameId })}?zoom=${getRoot().map.framing}`,
    (updater) => set((s) => ({ panels: { ...s.panels, map: updater(s.panels.map) } })),
    get,
  );
  const edges = createPanel<EdgesDashboardPayload>(
    (gameId) => endpoints.edges.path({ id: gameId }),
    (updater) => set((s) => ({ panels: { ...s.panels, edges: updater(s.panels.edges) } })),
    get,
  );
  const stateApparatus = createPanel<StateApparatusDashboard>(
    (gameId) => endpoints.stateApparatus.path({ id: gameId }),
    (updater) =>
      set((s) => ({
        panels: { ...s.panels, stateApparatus: updater(s.panels.stateApparatus) },
      })),
    get,
  );

  const wire = createPanel<WireFeed>(
    (gameId) => endpoints.wire.path({ id: gameId }),
    (updater) => set((s) => ({ panels: { ...s.panels, wire: updater(s.panels.wire) } })),
    get,
  );
  const contradiction = createPanel<ContradictionSnapshot>(
    (gameId) => endpoints.contradiction.path({ id: gameId }),
    (updater) =>
      set((s) => ({ panels: { ...s.panels, contradiction: updater(s.panels.contradiction) } })),
    get,
  );
  const endgame = createPanel<EndgameState>(
    (gameId) => endpoints.endgame.path({ id: gameId }),
    (updater) => set((s) => ({ panels: { ...s.panels, endgame: updater(s.panels.endgame) } })),
    get,
  );
  const objectives = createPanel<ObjectivesTracker>(
    (gameId) => endpoints.objectives.path({ id: gameId }),
    (updater) =>
      set((s) => ({ panels: { ...s.panels, objectives: updater(s.panels.objectives) } })),
    get,
  );
  const tradeFlows = createPanel<TradeFlowsPayload>(
    (gameId) => endpoints.tradeFlows.path({ id: gameId }),
    (updater) =>
      set((s) => ({ panels: { ...s.panels, tradeFlows: updater(s.panels.tradeFlows) } })),
    get,
  );
  const narration = createNarrationPanel(
    (updater) => set((s) => ({ panels: { ...s.panels, narration: updater(s.panels.narration) } })),
    () => get().panels.narration,
  );
  const network = createPanel<OrgNetworkPayload>(
    (gameId) => endpoints.orgNetwork.path({ id: gameId }),
    (updater) => set((s) => ({ panels: { ...s.panels, network: updater(s.panels.network) } })),
    get,
  );

  return {
    panels: {
      summary,
      timeseries,
      economy,
      communities,
      map: mapPanel,
      edges,
      stateApparatus,
      wire,
      contradiction,
      endgame,
      objectives,
      tradeFlows,
      narration,
      network,
    },
  };
};
