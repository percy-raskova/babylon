/**
 * Session slice — auth + game session id + lobby state (spec-110 B3).
 *
 * Mirrors the real Django endpoints used by the legacy app's `App.tsx` /
 * `LoginPage.tsx` / `GameList.tsx` (`web/frontend/src`): `/accounts/whoami/`,
 * `/accounts/login/` (form-encoded), `/accounts/logout/`, `/api/games/`
 * (GET list / POST create), `/api/scenarios/`. No invented endpoints
 * (Constitution III.11) — every path here is read verbatim off the old app.
 */

import type { StateCreator } from "zustand";
import { get as apiGet, post as apiPost, postForm as apiPostForm } from "@/api/client";
import type { AuthState, GameSummary, ScenarioInfo, CreateGameParams } from "@/types/game";
import type { RootState } from "../types";

export interface SessionSlice {
  session: {
    auth: AuthState | null;
    /** True while the initial `/accounts/whoami/` check is in flight. */
    authChecking: boolean;
    games: GameSummary[];
    gamesLoading: boolean;
    scenarios: ScenarioInfo[];
    /** The game session currently in view (drives every other slice's fetches). */
    activeGameId: string | null;
    error: string | null;

    checkAuth: () => Promise<void>;
    login: (username: string, password: string) => Promise<boolean>;
    logout: () => Promise<void>;
    fetchGames: () => Promise<void>;
    fetchScenarios: () => Promise<void>;
    /** Returns the new session id on success, or null on failure. */
    createGame: (params: CreateGameParams) => Promise<string | null>;
    setActiveGame: (id: string | null) => void;
  };
}

export const createSessionSlice: StateCreator<RootState, [], [], SessionSlice> = (set, get) => ({
  session: {
    auth: null,
    authChecking: true,
    games: [],
    gamesLoading: false,
    scenarios: [],
    activeGameId: null,
    error: null,

    checkAuth: async () => {
      set((s) => ({ session: { ...s.session, authChecking: true } }));
      const res = await apiGet<AuthState>("/accounts/whoami/");
      set((s) => ({
        session: {
          ...s.session,
          auth: res.status === "ok" && res.data.is_authenticated ? res.data : null,
          authChecking: false,
        },
      }));
    },

    login: async (username, password) => {
      set((s) => ({ session: { ...s.session, error: null } }));
      const res = await apiPostForm<{ username: string }>("/accounts/login/", {
        username,
        password,
      });
      if (res.status === "ok") {
        set((s) => ({
          session: {
            ...s.session,
            auth: { is_authenticated: true, username: res.data.username },
          },
        }));
        return true;
      }
      set((s) => ({ session: { ...s.session, error: res.message ?? "Login failed" } }));
      return false;
    },

    logout: async () => {
      await apiPost("/accounts/logout/");
      set((s) => ({
        session: {
          ...s.session,
          auth: null,
          activeGameId: null,
          games: [],
        },
      }));
    },

    fetchGames: async () => {
      set((s) => ({ session: { ...s.session, gamesLoading: true } }));
      const res = await apiGet<GameSummary[]>("/api/games/");
      if (res.status === "ok") {
        set((s) => ({ session: { ...s.session, games: res.data, gamesLoading: false } }));
      } else {
        set((s) => ({
          session: {
            ...s.session,
            gamesLoading: false,
            error: res.message ?? "Failed to load games",
          },
        }));
      }
    },

    fetchScenarios: async () => {
      const res = await apiGet<ScenarioInfo[]>("/api/scenarios/");
      if (res.status === "ok") {
        set((s) => ({ session: { ...s.session, scenarios: res.data } }));
      } else {
        set((s) => ({
          session: { ...s.session, error: res.message ?? "Failed to load scenarios" },
        }));
      }
    },

    createGame: async (params) => {
      const res = await apiPost<{ session_id: string }>("/api/games/", params);
      if (res.status === "ok") {
        await get().session.fetchGames();
        return res.data.session_id;
      }
      set((s) => ({ session: { ...s.session, error: res.message ?? "Failed to create game" } }));
      return null;
    },

    setActiveGame: (id) => set((s) => ({ session: { ...s.session, activeGameId: id } })),
  },
});
