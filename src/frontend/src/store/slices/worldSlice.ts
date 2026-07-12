/**
 * World slice — the latest `/state/` snapshot, and the one place the
 * fetch orchestrator's "observed a tick change" path lives (spec-110 B3).
 *
 * `fetchState` is called both by the heartbeat and by a local resolve
 * (`timeSlice`) — either way, when the observed tick differs from the
 * last one this slice saw, it fans out exactly one refetch to every
 * *mounted* docked panel and checks the new tick's events for a critical
 * one, autopausing the time slice if so. Panels never own their own
 * timers or tick-comparison logic — this is the one path.
 */

import type { StateCreator } from "zustand";
import { get as apiGet } from "@/api/client";
import { classifyEvents } from "@/lib/eventClassifier";
import type { GameSnapshot } from "@/types/game";
import type { RootState } from "../types";
import { PANEL_KEYS, TAKEOVER_PANEL_KEYS } from "./panels";

export interface WorldSlice {
  world: {
    snapshot: GameSnapshot | null;
    /** Tick of the last snapshot this slice observed, or `null` before the first fetch. */
    lastTick: number | null;
    loading: boolean;
    error: string | null;
    fetchState: (gameId: string) => Promise<void>;
  };
}

async function onTickAdvanced(
  get: () => RootState,
  gameId: string,
  snap: GameSnapshot,
  isGenuineAdvance: boolean,
) {
  const panels = get().panels;
  // `endgame` is deliberately excluded from the generic mounted-only
  // fan-out below and fetched unconditionally instead (spec-113 §4.4
  // correction): the auto-open watcher needs to observe its `outcome`
  // transition even before any takeover ever mounts `useEndgame`.
  const prevEndgameOutcome = panels.endgame.data?.outcome ?? null;

  await Promise.all([
    ...PANEL_KEYS.filter((key) => panels[key].mounted).map((key) => panels[key].fetch(gameId)),
    ...TAKEOVER_PANEL_KEYS.filter((key) => key !== "endgame" && panels[key].mounted).map((key) =>
      panels[key].fetch(gameId),
    ),
    panels.endgame.fetch(gameId),
  ]);

  // A resolve consumes every action queued against the prior tick — the
  // Action Composer's pending list no longer describes reality once the
  // tick it was submitted against is gone. Only a genuine tick change (not
  // the initial null -> first-snapshot load) means a resolve happened.
  if (isGenuineAdvance) {
    get().actions.clearPending();
  }

  // events.ingest is idempotent per tick (dedup guard) — safe to call on
  // every observed tick, including the initial null -> first-snapshot load.
  get().events.ingest(snap.tick, snap.events);

  const criticalIds = classifyEvents(snap.events)
    .filter((e) => e.severity === "critical")
    .map((e) => e.id);
  if (criticalIds.length > 0) {
    get().time.autopause(criticalIds);
  }

  // Endgame auto-open (spec-113 §4.4 correction, owner item 37): the real
  // endgame signal is `panels.endgame.data.outcome` transitioning
  // null -> non-null, NOT `GameSnapshot.endgame` (a dead field with zero
  // readers). Firing only on that transition — never on an already-non-null
  // outcome staying non-null — is what makes this exactly-once per game.
  const newEndgameOutcome = get().panels.endgame.data?.outcome ?? null;
  if (prevEndgameOutcome === null && newEndgameOutcome !== null) {
    get().time.pause();
    get().ui.openTakeover("chronicle");
  }
}

export const createWorldSlice: StateCreator<RootState, [], [], WorldSlice> = (set, get) => ({
  world: {
    snapshot: null,
    lastTick: null,
    loading: false,
    error: null,

    fetchState: async (gameId) => {
      set((s) => ({ world: { ...s.world, loading: true, error: null } }));
      const res = await apiGet<GameSnapshot>(`/api/games/${gameId}/state/`);

      if (res.status !== "ok") {
        set((s) => ({
          world: { ...s.world, loading: false, error: res.message ?? "Failed to load game state" },
        }));
        return;
      }

      const snap = res.data;
      const prevTick = get().world.lastTick;
      const prevSnapshot = get().world.snapshot;

      // Same tick, byte-identical payload (JSON.stringify — cheap enough
      // once per HEARTBEAT_MS): keep the previous snapshot object so
      // referentially-memoized consumers (DeckGLMap's `layers`) don't
      // rebuild on an unchanged beat. Any actual content difference must
      // still replace the reference — this is NOT a same-tick skip.
      const isDuplicateBeat =
        prevSnapshot !== null &&
        snap.tick === prevTick &&
        JSON.stringify(snap) === JSON.stringify(prevSnapshot);

      if (isDuplicateBeat) {
        set((s) => ({ world: { ...s.world, loading: false } }));
      } else {
        set((s) => ({
          world: { ...s.world, snapshot: snap, lastTick: snap.tick, loading: false },
        }));
      }

      if (prevTick === null || snap.tick !== prevTick) {
        await onTickAdvanced(get, gameId, snap, prevTick !== null && snap.tick !== prevTick);
      }
    },
  },
});
