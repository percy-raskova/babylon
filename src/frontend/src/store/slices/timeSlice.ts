/**
 * Time slice — the resolve state machine (spec-110 B4).
 *
 * States: paused | playing | resolving(prevTick) | autopaused(eventIds) |
 * error(message). `playIntent` is an internal flag (not itself an
 * observable `status`) that lets `pause()` register during an in-flight
 * resolve — the recursive `resolveOnce` loop checks it after every
 * awaited step, so a pause requested mid-resolve still takes effect the
 * instant that resolve's refetch completes, without needing to abort an
 * in-flight request.
 *
 * `resolveOnce` recurses only while `playIntent` stays true and the
 * previous resolve fully completed (POST /resolve/ + its state refetch +
 * fan-out) — this is Play's "strictly serialized loop": the next resolve
 * is never scheduled until the previous one's refetch has landed, and it
 * always terminates (pause / 5xx-error / autopause on a critical event
 * all flip `playIntent` false or exit before recursing), so the depth is
 * bounded by wall-clock ticks played, not open-ended.
 *
 * `speed` (spec-113 architecture §4.1) extends this without touching any
 * of the above: it sets the **inter-resolve delay** injected at
 * `settleAfterResolve`'s single recursion point, right before scheduling
 * the next `resolveOnce`. Nothing else about the loop changes — `speed` is
 * read fresh via `get().time.speed` on every recursion, so a mid-loop
 * `setSpeed()` call takes effect on the very next delay, and the delay
 * re-checks `playIntent`/`status` after waking so a `pause()` (or an
 * autopause) that lands *during* the delay still stops the loop instead of
 * forcing one more resolve through. Default speed is 5 ("current behavior"
 * per architecture §4.1 — zero injected delay), so every pre-existing
 * timeSlice test (none of which calls `setSpeed`) sees exactly the same
 * zero-delay loop as before.
 */

import type { StateCreator } from "zustand";
import { post as apiPost } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import type { RootState } from "../types";

export type TimeStatus = "paused" | "playing" | "resolving" | "autopaused" | "error";

/** The three selectable auto-resolve speeds (architecture §4.1). */
export type TimeSpeed = 1 | 2 | 5;

/**
 * Inter-resolve delay per speed. 5x is exactly 0ms — "current behavior" per
 * architecture §4.1 — not merely small, so any test that never touches
 * `speed` sees a byte-for-byte-identical zero-delay loop.
 */
const SPEED_DELAY_MS: Record<TimeSpeed, number> = { 1: 800, 2: 300, 5: 0 };

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export interface TimeSlice {
  time: {
    status: TimeStatus;
    /** Tick in effect when the current/last resolve started. */
    prevTick: number | null;
    /** Event ids that triggered the most recent autopause. */
    autopauseEventIds: string[];
    /** Loud failure message (III.11) — set on 5xx/network failures only. */
    errorMessage: string | null;
    /** Internal — whether the Play loop should keep scheduling resolves. */
    playIntent: boolean;
    /** Auto-resolve speed — sets the inter-resolve delay (architecture §4.1). */
    speed: TimeSpeed;

    /** Exactly one POST /resolve/. Only valid from `paused`. */
    step: (gameId: string) => Promise<void>;
    /** Start the serialized auto-resolve loop. Only valid from `paused`. */
    play: (gameId: string) => Promise<void>;
    /** Stop the loop after the in-flight resolve (if any) completes. */
    pause: () => void;
    /** Acknowledge an `autopaused`/`error` state and return to `paused`. */
    resume: () => void;
    /** Called by `worldSlice` when a newly-observed tick carries a critical event. */
    autopause: (eventIds: string[]) => void;
    /** Spacebar handler — paused → play, playing → pause, no-op otherwise. */
    toggleSpacebar: (gameId: string) => void;
    /** Set the auto-resolve speed. Valid in any status — takes effect on the next delay. */
    setSpeed: (speed: TimeSpeed) => void;
  };
}

export const createTimeSlice: StateCreator<RootState, [], [], TimeSlice> = (set, get) => {
  const resolveOnce = async (gameId: string, auto: boolean): Promise<void> => {
    const prevTick = get().world.snapshot?.tick ?? 0;
    set((s) => ({ time: { ...s.time, status: "resolving", prevTick } }));

    const res = await apiPost<Record<string, unknown>>(endpoints.resolveTick.path({ id: gameId }));

    if (res.status === "ok") {
      await get().world.fetchState(gameId);
      await settleAfterResolve(gameId, auto);
      return;
    }

    if (res.http_status === 409) {
      // An external resolve is already in flight — resync and, if still
      // playing, retry; a manual step just goes back to paused.
      await get().world.fetchState(gameId);
      await settleAfterResolve(gameId, auto);
      return;
    }

    // 5xx / network / anything else — loud failure, no silent retry (III.11).
    set((s) => ({
      time: {
        ...s.time,
        status: "error",
        errorMessage: res.message ?? "Tick resolution failed",
        playIntent: false,
      },
    }));
  };

  /** Shared tail for both the ok and 409 branches of `resolveOnce`. */
  const settleAfterResolve = async (gameId: string, auto: boolean): Promise<void> => {
    if (get().time.status === "autopaused") return; // world slice already took over
    if (auto && get().time.playIntent) {
      set((s) => ({ time: { ...s.time, status: "playing" } }));

      // The single delay-injection point (architecture §4.1's "speed only
      // sets the inter-resolve delay"): read fresh so a mid-loop
      // `setSpeed()` applies to the very next wait, not just future loops.
      // Always awaited, even at 0ms (5x): `setTimeout` still yields to the
      // macrotask queue once, which is what lets a `pause()` call (or any
      // other timer-driven event) actually get scheduled between resolves.
      // Skipping the await entirely at 0ms would chain every recursion
      // through pure microtasks with no yield point at all, which can
      // starve the macrotask queue outright (observed: it froze `pause()`'s
      // own timer forever under a fast mock resolver).
      await sleep(SPEED_DELAY_MS[get().time.speed]);

      // Re-check after the delay — a pause() (or an autopause landing via
      // some other path) requested while we were waiting must still stop
      // the loop here rather than forcing one more resolve through.
      if (get().time.status === "autopaused") return;
      if (!get().time.playIntent) {
        set((s) => ({ time: { ...s.time, status: "paused", playIntent: false } }));
        return;
      }

      await resolveOnce(gameId, true);
    } else {
      set((s) => ({ time: { ...s.time, status: "paused", playIntent: false } }));
    }
  };

  return {
    time: {
      status: "paused",
      prevTick: null,
      autopauseEventIds: [],
      errorMessage: null,
      playIntent: false,
      speed: 5,

      step: async (gameId) => {
        if (get().time.status !== "paused") return;
        await resolveOnce(gameId, false);
      },

      play: async (gameId) => {
        if (get().time.status !== "paused") return;
        set((s) => ({ time: { ...s.time, status: "playing", playIntent: true } }));
        await resolveOnce(gameId, true);
      },

      pause: () => {
        set((s) => ({
          time: {
            ...s.time,
            playIntent: false,
            status: s.time.status === "playing" ? "paused" : s.time.status,
          },
        }));
      },

      resume: () => {
        const status = get().time.status;
        if (status !== "autopaused" && status !== "error") return;
        set((s) => ({
          time: { ...s.time, status: "paused", autopauseEventIds: [], errorMessage: null },
        }));
      },

      autopause: (eventIds) =>
        set((s) => ({
          time: { ...s.time, status: "autopaused", autopauseEventIds: eventIds, playIntent: false },
        })),

      toggleSpacebar: (gameId) => {
        const status = get().time.status;
        if (status === "paused") {
          get().time.play(gameId);
        } else if (status === "playing") {
          get().time.pause();
        }
      },

      setSpeed: (speed) => set((s) => ({ time: { ...s.time, speed } })),
    },
  };
};
