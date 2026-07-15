/**
 * Map-replay slice — the RADAR LOOP tick scrubber's state (Program 17 Wave
 * 3, Frontend-W3R3). Distinct from `mapSlice` (view *controls* — active
 * lens/framing/selection) and `panels.map` (the fetched live GeoJSON for
 * the current tick): this slice owns ONE fetched historical window —
 * `GET /api/games/{id}/map/history/?metric=<name>` — plus client-side
 * scrub position over it. Mirrors `mapSlice.ts`'s idiom (a nested state
 * object with its own setters, `StateCreator<RootState, [], [], XSlice>`)
 * rather than `panels/panelFactory.ts`'s `Panel<T>` shape — the fetch here
 * takes a `metric` argument and is user-triggered (`enter`), not a
 * tick-driven `PANEL_KEYS` fan-out target, and this slice owns extra
 * scrub/step/live-tick-affordance behavior `Panel<T>` has no room for.
 *
 * Exactly one fetch per `enter(gameId, metric)` call — the scrubber then
 * pages through the ALREADY-FETCHED `frames` window client-side
 * (`scrubTo`/`step`), never issuing a new request per frame.
 */

import type { StateCreator } from "zustand";
import type { RootState } from "../types";
import type { MapMetric } from "@/lib/lens";
import type { MapHistoryFrame } from "@/types/game";
import { fetchMapHistory } from "@/api/client";

export type MapReplayStatus = "idle" | "loading" | "ready" | "error";

export interface MapReplayState {
  active: boolean;
  metric: MapMetric | null;
  frames: MapHistoryFrame[];
  currentIndex: number;
  /** True when the backend served a narrower window than requested (its 128-tick cap). */
  capped: boolean;
  status: MapReplayStatus;
  error: string | null;
  /**
   * Highest live tick observed while replay is active but newer than the
   * fetched window's last frame — the panel's "live tick N available"
   * affordance (Constitution III.11-adjacent UX rule: never yank the
   * scrubber out from under the player). `null` when nothing newer has
   * arrived, or replay is inactive.
   */
  liveTickAvailable: number | null;
}

export interface MapReplaySlice {
  mapReplay: MapReplayState & {
    /** Fetch `metric`'s history window for `gameId` and enter replay mode. Safe to call while already active (re-enters with a fresh window). */
    enter: (gameId: string, metric: MapMetric) => Promise<void>;
    /** Leave replay mode and reset every field to its idle default (frame invariance — no residual state for the map to keep reading). */
    exit: () => void;
    /** Move the scrubber to `index`, clamped to `[0, frames.length - 1]`. */
    scrubTo: (index: number) => void;
    /** Step the scrubber by `direction` (+1/-1), clamped at either end — the frame-stepper's per-tick advance. */
    step: (direction: 1 | -1) => void;
    /** Record the current live tick; sets `liveTickAvailable` when it is newer than the fetched window and replay is active, clears it otherwise. */
    noteLiveTick: (tick: number) => void;
  };
}

const INITIAL_STATE: MapReplayState = {
  active: false,
  metric: null,
  frames: [],
  currentIndex: 0,
  capped: false,
  status: "idle",
  error: null,
  liveTickAvailable: null,
};

/** Clamp `index` into the valid `[0, frameCount - 1]` range (`0` for an empty window). */
function clampIndex(index: number, frameCount: number): number {
  if (frameCount === 0) return 0;
  return Math.max(0, Math.min(frameCount - 1, index));
}

export const createMapReplaySlice: StateCreator<RootState, [], [], MapReplaySlice> = (
  set,
  get,
) => ({
  mapReplay: {
    ...INITIAL_STATE,

    enter: async (gameId, metric) => {
      set((s) => ({
        mapReplay: {
          ...s.mapReplay,
          active: true,
          metric,
          status: "loading",
          error: null,
          liveTickAvailable: null,
        },
      }));

      const res = await fetchMapHistory(gameId, metric);

      if (res.status !== "ok") {
        set((s) => ({
          mapReplay: {
            ...s.mapReplay,
            status: "error",
            error: res.message ?? "Failed to load map history",
            frames: [],
            currentIndex: 0,
          },
        }));
        return;
      }

      set((s) => ({
        mapReplay: {
          ...s.mapReplay,
          frames: res.data.frames,
          capped: res.data.capped,
          currentIndex: clampIndex(res.data.frames.length - 1, res.data.frames.length),
          status: "ready",
          error: null,
        },
      }));
    },

    exit: () => set((s) => ({ mapReplay: { ...s.mapReplay, ...INITIAL_STATE } })),

    scrubTo: (index) =>
      set((s) => ({
        mapReplay: { ...s.mapReplay, currentIndex: clampIndex(index, s.mapReplay.frames.length) },
      })),

    step: (direction) =>
      set((s) => ({
        mapReplay: {
          ...s.mapReplay,
          currentIndex: clampIndex(s.mapReplay.currentIndex + direction, s.mapReplay.frames.length),
        },
      })),

    noteLiveTick: (tick) => {
      const { active, frames } = get().mapReplay;
      const lastFrameTick = frames.at(-1)?.tick;
      const isNewer = active && lastFrameTick !== undefined && tick > lastFrameTick;
      set((s) => ({
        mapReplay: { ...s.mapReplay, liveTickAvailable: isNewer ? tick : null },
      }));
    },
  },
});
