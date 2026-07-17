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
import { get as apiGet, post as apiPost } from "@/api/client";
import { endpoints, type EndpointResponse } from "@/api/endpoints";
import { classifyEvents } from "@/lib/eventClassifier";
import { computeAutopauseDecision } from "@/lib/eventDedup";
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
    /**
     * Spec-116 FR-116-5 — the mercy affordance: POST accept-outcome, then
     * refetch the endgame panel so the pre-existing outcome watcher (below)
     * opens the chronicle takeover on the same null -> non-null transition
     * it already detects from `onTickAdvanced` (no new watcher).
     */
    acceptOutcome: (gameId: string) => Promise<void>;
  };
}

/**
 * The endgame auto-open check (spec-113 §4.4 correction, owner item 37):
 * fires the chronicle takeover exactly once, on `panels.endgame.data.outcome`
 * transitioning null -> non-null. Shared by `onTickAdvanced`'s per-tick fan-out
 * and `acceptOutcome`'s direct endgame refetch (spec-116 FR-116-5) — the same
 * watcher, not a duplicate.
 */
function maybeOpenChronicleOnEndgame(
  get: () => RootState,
  prevEndgameOutcome: string | null,
): void {
  const newEndgameOutcome = get().panels.endgame.data?.outcome ?? null;
  if (prevEndgameOutcome === null && newEndgameOutcome !== null) {
    get().time.pause();
    get().ui.openTakeover("chronicle");
  }
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

  // Autopause-once (spec-116 FR-116-2 iii): a distinct (event_type, subject)
  // fires at most once per session; ENDGAME acknowledges per-occurrence
  // (key@tick) so it always fires on a new occurrence. Mark-then-pause is
  // a synchronous check-and-set, so the GameRoute-vs-heartbeat load race
  // (both racers seeing prevTick===null) cannot double-fire — the loser
  // finds the keys already acknowledged.
  const criticalEvents = classifyEvents(snap.events)
    .filter((e) => e.severity === "critical")
    .map((e) => e.event);
  const acknowledged = new Set(get().events.acknowledgedAutopauseKeys);
  const decision = computeAutopauseDecision(criticalEvents, acknowledged);
  if (decision.firingKeys.length > 0) {
    get().events.acknowledgeAutopauseKeys(decision.acknowledgementKeys);
    get().time.autopause(decision.firingKeys);
  }

  // Endgame auto-open (spec-113 §4.4 correction, owner item 37): the real
  // endgame signal is `panels.endgame.data.outcome` transitioning
  // null -> non-null, NOT `GameSnapshot.endgame` (a dead field with zero
  // readers). Firing only on that transition — never on an already-non-null
  // outcome staying non-null — is what makes this exactly-once per game.
  maybeOpenChronicleOnEndgame(get, prevEndgameOutcome);
}

export const createWorldSlice: StateCreator<RootState, [], [], WorldSlice> = (set, get) => ({
  world: {
    snapshot: null,
    lastTick: null,
    loading: false,
    error: null,

    fetchState: async (gameId) => {
      set((s) => ({ world: { ...s.world, loading: true, error: null } }));
      const res = await apiGet<GameSnapshot>(endpoints.gameState.path({ id: gameId }));

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

    acceptOutcome: async (gameId) => {
      const prevEndgameOutcome = get().panels.endgame.data?.outcome ?? null;
      const res = await apiPost<EndpointResponse<typeof endpoints.acceptOutcome>>(
        endpoints.acceptOutcome.path({ id: gameId }),
      );
      if (res.status !== "ok") return;

      await get().panels.endgame.fetch(gameId);
      maybeOpenChronicleOnEndgame(get, prevEndgameOutcome);
    },
  },
});
