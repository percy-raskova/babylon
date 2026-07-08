/**
 * Game state store — manages session, snapshot, and tick history.
 */

import { create } from "zustand";
import { get as apiGet, post as apiPost } from "@/api/client";
import { createLogger } from "@/utils/logger";
import { classifyEvents } from "@/lib/eventClassifier";
import { useUIStore } from "./uiStore";
import { useMapStore } from "./mapStore";

const log = createLogger("GameStore");
import type {
  GameSnapshot,
  OrgState,
  AvailableAction,
  SubmitActionParams,
  ActionResultData,
  AdminLevel,
  PlayerVerb,
} from "@/types/game";

/** Aggregated metrics for one tick, used for time series. */
export interface TickSummary {
  tick: number;
  avgHeat: number;
  avgConsciousness: number;
  totalWealth: number;
  orgCount: number;
  eventCount: number;
  edgeCount: number;
}

function extractSummary(snap: GameSnapshot): TickSummary {
  const territories = snap.territories;
  const orgs = snap.organizations;

  const avgHeat =
    territories.length > 0 ? territories.reduce((s, t) => s + t.heat, 0) / territories.length : 0;

  // Use org revolutionary consciousness as the aggregate consciousness metric
  const avgConsciousness =
    orgs.length > 0
      ? orgs.reduce((s, o) => s + (o.consciousness?.revolutionary ?? 0), 0) / orgs.length
      : 0;

  // Total wealth = sum of org budgets
  const totalWealth = orgs.reduce((s, o) => s + o.budget, 0);

  return {
    tick: snap.tick,
    avgHeat,
    avgConsciousness,
    totalWealth,
    orgCount: snap.organizations.length,
    eventCount: snap.events.length,
    edgeCount: snap.edges.length,
  };
}

/**
 * Classify and accumulate events from a snapshot into the UI notification buffer.
 */
function accumulateEvents(snap: GameSnapshot): void {
  if (snap.events.length === 0) return;
  const classified = classifyEvents(snap.events);
  useUIStore.getState().addEvents(classified);
}

import type { FeatureCollection } from "geojson";

interface GameState {
  sessionId: string | null;
  snapshot: GameSnapshot | null;
  mapData: FeatureCollection | null;
  available: AvailableAction[];
  tickSummaries: TickSummary[];
  loading: boolean;
  error: string | null;

  /** Player-owned organizations (from /organizations/?player_only=true). */
  playerOrgs: OrgState[];
  /** Whether playerOrgs have been fetched at least once. */
  playerOrgsLoaded: boolean;
  /** Verb target data cache, keyed by `${verb}:${orgId}`. */
  verbTargets: Record<string, Record<string, unknown>>;

  setSession: (id: string | null) => void;
  fetchState: (gameId: string) => Promise<void>;
  fetchMapData: (gameId: string, zoom: AdminLevel) => Promise<void>;
  submitAction: (gameId: string, params: SubmitActionParams) => Promise<void>;
  resolveTick: (gameId: string) => Promise<ActionResultData[] | null>;
  fetchPlayerOrgs: (gameId: string) => Promise<void>;
  fetchVerbTargets: (gameId: string, verb: PlayerVerb, orgId: string) => Promise<void>;
  invalidateVerbTargets: () => void;
  reset: () => void;
}

export const useGameStore = create<GameState>((set, get) => ({
  sessionId: null,
  snapshot: null,
  mapData: null,
  available: [],
  tickSummaries: [],
  loading: false,
  error: null,
  playerOrgs: [],
  playerOrgsLoaded: false,
  verbTargets: {},

  // (omitting setSession code modification by replacing only the relevant section)

  setSession: (id) => set({ sessionId: id }),

  fetchState: async (gameId) => {
    set({ loading: true, error: null });
    log.debug("Fetching game state", { gameId });

    const zoom = useMapStore.getState().activeFraming;
    const [stateRes, actionsRes, mapRes] = await Promise.all([
      apiGet<GameSnapshot>(`/api/games/${gameId}/state/`),
      apiGet<AvailableAction[]>(`/api/games/${gameId}/actions/available/`),
      apiGet<FeatureCollection>(`/api/games/${gameId}/map/?zoom=${zoom}`),
    ]);

    if (stateRes.status === "ok") {
      const snap = stateRes.data;
      const summaries = get().tickSummaries;
      const summary = extractSummary(snap);
      const lastTick = summaries[summaries.length - 1]?.tick ?? -1;
      const newSummaries = summary.tick !== lastTick ? [...summaries, summary] : summaries;

      set({ snapshot: snap, tickSummaries: newSummaries });

      // Accumulate events into notification buffer (only for new ticks)
      if (summary.tick !== lastTick) {
        accumulateEvents(snap);
      }
    } else {
      set({ error: stateRes.message ?? "Failed to load game state" });
    }

    if (actionsRes.status === "ok") {
      set({ available: actionsRes.data });
    }

    if (mapRes.status === "ok") {
      set({ mapData: mapRes.data });
    }

    set({ loading: false });
  },

  fetchMapData: async (gameId, zoom) => {
    log.debug("Fetching map data", { gameId, zoom });
    const res = await apiGet<FeatureCollection>(`/api/games/${gameId}/map/?zoom=${zoom}`);
    if (res.status === "ok") {
      set({ mapData: res.data });
    }
  },

  submitAction: async (gameId, params) => {
    log.info("Submitting action", { gameId, params });
    // Spec 040: verb is in the URL path, not the request body
    const { verb, ...body } = params;
    const res = await apiPost(`/api/games/${gameId}/actions/${verb}/`, body);
    if (res.status !== "ok") {
      log.error("Action submission failed", { gameId, message: res.message });
      set({ error: res.message ?? "Failed to submit action" });
      return; // Don't re-fetch — error would be cleared
    }
    await get().fetchState(gameId);
  },

  resolveTick: async (gameId) => {
    log.info("Resolving tick", { gameId });
    const res = await apiPost<Record<string, unknown>>(`/api/games/${gameId}/resolve/`);
    if (res.status !== "ok") {
      log.error("Tick resolution failed", { gameId, message: res.message });
      set({ error: res.message ?? "Failed to resolve tick" });
      return null;
    }
    log.info("Tick resolved", { gameId, newTick: res.tick });
    // Targets are tick-stale — invalidate before re-fetching state.
    get().invalidateVerbTargets();
    await get().fetchState(gameId);
    const tick = res.tick ?? 0;
    const resultsRes = await apiGet<ActionResultData[]>(`/api/games/${gameId}/results/${tick}/`);
    return resultsRes.status === "ok" ? resultsRes.data : null;
  },

  fetchPlayerOrgs: async (gameId) => {
    log.debug("Fetching player orgs", { gameId });
    const res = await apiGet<{ organizations: OrgState[] }>(
      `/api/games/${gameId}/organizations/?player_only=true`,
    );
    if (res.status === "ok") {
      set({ playerOrgs: res.data.organizations, playerOrgsLoaded: true });
    } else {
      log.error("Failed to fetch player orgs", { gameId, message: res.message });
      set({ error: res.message ?? "Failed to fetch player organizations" });
    }
  },

  fetchVerbTargets: async (gameId, verb, orgId) => {
    const cacheKey = `${verb}:${orgId}`;
    log.debug("Fetching verb targets", { gameId, verb, orgId });
    const res = await apiGet<Record<string, unknown>>(
      `/api/games/${gameId}/actions/${verb}/targets/?org_id=${orgId}`,
    );
    if (res.status !== "error") {
      // Verb target endpoints return flat responses (targets, cost, etc.
      // at top level) rather than using the standard {status, data} envelope.
      // Some (mobilize) have no status field at all, so res.status is
      // undefined on success — the client only synthesizes status:"error"
      // on failures. Store res.data if present, else the full flat body.
      const payload = (res.data ?? res) as Record<string, unknown>;
      set((s) => ({
        verbTargets: { ...s.verbTargets, [cacheKey]: payload },
      }));
    } else {
      log.error("Failed to fetch verb targets", { gameId, verb, orgId, message: res.message });
      set({ error: res.message ?? "Failed to fetch action targets" });
    }
  },

  invalidateVerbTargets: () => {
    set({ verbTargets: {} });
  },

  reset: () =>
    set({
      sessionId: null,
      snapshot: null,
      mapData: null,
      available: [],
      tickSummaries: [],
      loading: false,
      error: null,
      playerOrgs: [],
      playerOrgsLoaded: false,
      verbTargets: {},
    }),
}));
