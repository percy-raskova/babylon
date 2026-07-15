/**
 * Panel factory — one shape reused for every docked panel (spec-110 B3).
 *
 * A "panel" owns exactly one GET endpoint: `data` from its last successful
 * fetch, `loading`/`error` for that fetch, and `mounted` so the fetch
 * orchestrator's tick-fan-out only refetches panels a component actually
 * has on screen (`onTickAdvanced` never fetches an unmounted panel —
 * that's the whole point of replacing 13 independent pollers with one
 * heartbeat that fans out to what's visible).
 */

import { get as apiGet } from "@/api/client";
import type { RootState } from "../../types";

export interface PanelState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  mounted: boolean;
}

export interface Panel<T> extends PanelState<T> {
  /** Fetch this panel's endpoint for `gameId`. Safe to call concurrently. */
  fetch: (gameId: string) => Promise<void>;
  /** Mark this panel on/off screen — governs tick-fan-out eligibility. */
  setMounted: (mounted: boolean) => void;
}

/**
 * Build one `Panel<T>` bound to `endpoint(gameId)`.
 *
 * `updateSelf` is supplied by the composing slice (`panels/index.ts`) and
 * knows how to splice this one panel's updated state back into the root
 * store — each panel gets its own closure over `set`, so concurrent
 * fetches on sibling panels never clobber each other (every `set` call
 * here only ever touches `panels.<thisKey>`). The updater always spreads
 * the *whole* `Panel<T>` (state fields + `fetch`/`setMounted`), so the
 * method references stay stable across state updates.
 */
export function createPanel<T>(
  endpoint: (gameId: string, get: () => RootState) => string,
  updateSelf: (updater: (p: Panel<T>) => Panel<T>) => void,
  get: () => RootState,
): Panel<T> {
  const fetch = async (gameId: string): Promise<void> => {
    updateSelf((p) => ({ ...p, loading: true, error: null }));
    const res = await apiGet<T>(endpoint(gameId, get));
    if (res.status === "ok") {
      updateSelf((p) => ({ ...p, data: res.data, loading: false, error: null }));
    } else {
      updateSelf((p) => ({
        ...p,
        loading: false,
        error: res.message ?? "Failed to load panel data",
      }));
    }
  };

  const setMounted = (mounted: boolean): void => updateSelf((p) => ({ ...p, mounted }));

  return { data: null, loading: false, error: null, mounted: false, fetch, setMounted };
}

/** The 7 tick-driven docked panels the fetch orchestrator fans out to. */
export const PANEL_KEYS = [
  "summary",
  "timeseries",
  "economy",
  "communities",
  "map",
  "edges",
  "stateApparatus",
] as const;
export type PanelKey = (typeof PANEL_KEYS)[number];

/**
 * The tick-driven takeover/dock panels (spec-110 B5) — Wire, Dialectic,
 * Chronicle, Objectives, and the Wire Index tab's bloc-flow lines. Same
 * "only fetch what's mounted" contract as `PANEL_KEYS`, kept as a separate
 * list rather than merged into it since these mount on takeover-open /
 * dock-tab-select, not on shell mount.
 */
export const TAKEOVER_PANEL_KEYS = [
  "wire",
  "contradiction",
  "endgame",
  "objectives",
  "tradeFlows",
  // narration (spec-113 Lane N + orchestrator wiring): same mounted-only
  // contract; its fetch is cumulative (since_tick cursor) and degrades to
  // an honest "offline" state while the backend endpoint is contract-only.
  "narration",
  // network (AW4-R2, the Network takeover) — same mounted-only contract:
  // one-shot fetch on takeover-open, refetched on every observed tick
  // change while the takeover stays open.
  "network",
] as const;
export type TakeoverPanelKey = (typeof TAKEOVER_PANEL_KEYS)[number];
