/**
 * Contract tests for the time slice (spec-110 B4) — the resolve state
 * machine: paused | playing | resolving(prevTick) | autopaused(eventIds) |
 * error(message).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import {
  resetMockGameState,
  resolveBehaviorQueue,
  requestLog,
  DEFAULT_GAME_ID,
} from "@/test/handlers";
import { makeEvent } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("time slice — step", () => {
  it("starts paused", () => {
    expect(useStore.getState().time.status).toBe("paused");
  });

  it("step() does exactly one POST /resolve/ and returns to paused", async () => {
    await useStore.getState().time.step(DEFAULT_GAME_ID);

    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);
    expect(useStore.getState().time.status).toBe("paused");
    expect(useStore.getState().world.snapshot?.tick).toBe(2); // 1 -> 2
  });

  it("step() is a no-op while not paused", async () => {
    resolveBehaviorQueue.push("ok");
    const first = useStore.getState().time.step(DEFAULT_GAME_ID); // now "resolving"
    await useStore.getState().time.step(DEFAULT_GAME_ID); // should no-op
    await first;

    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);
  });

  it("transitions through resolving with the prior tick recorded", async () => {
    // Seed world.snapshot first — prevTick reads from it, and it's null
    // until the first fetchState.
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    expect(useStore.getState().world.snapshot?.tick).toBe(1);

    const promise = useStore.getState().time.step(DEFAULT_GAME_ID);
    expect(useStore.getState().time.status).toBe("resolving");
    expect(useStore.getState().time.prevTick).toBe(1);
    await promise;
  });
});

describe("time slice — 409 and 5xx", () => {
  it("409 resyncs state and returns to paused on a manual step (no error)", async () => {
    resolveBehaviorQueue.push("409");

    await useStore.getState().time.step(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("paused");
    expect(useStore.getState().time.errorMessage).toBeNull();
    // Resynced via a GET /state/ even though the resolve itself failed.
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);
  });

  it("5xx transitions to a loud error state and does not silently retry", async () => {
    resolveBehaviorQueue.push("500");

    await useStore.getState().time.step(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("error");
    expect(useStore.getState().time.errorMessage).toBe("Tick resolution failed");
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);
  });

  it("resume() clears an error state back to paused", async () => {
    resolveBehaviorQueue.push("500");
    await useStore.getState().time.step(DEFAULT_GAME_ID);
    expect(useStore.getState().time.status).toBe("error");

    useStore.getState().time.resume();

    expect(useStore.getState().time.status).toBe("paused");
    expect(useStore.getState().time.errorMessage).toBeNull();
  });
});

describe("time slice — autopause", () => {
  it("a critical event during step() lands in autopaused with the firing event ids", async () => {
    // The mock resolve clears events, so seed the *next* fetch's events by
    // overriding /state/ once the tick has advanced.
    server.use(
      http.post("/api/games/:id/resolve/", () =>
        HttpResponse.json({ status: "ok", data: { resolved: true }, tick: 2 }),
      ),
      http.get("/api/games/:id/state/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            tick: 2,
            session_id: DEFAULT_GAME_ID,
            organizations: [],
            institutions: [],
            territories: [],
            hyperedges: [],
            edges: [],
            events: [makeEvent({ type: "rupture", tick: 2 })],
            derived: {
              value_tensor: {
                departments: [],
                components: [],
                values: [],
                conservation_residual: 0,
              },
              imperial_rent: {
                unequal_exchange: 0,
                externalized_reproductive: 0,
                domestic_shadow: 0,
                total: 0,
              },
              dept_iii_visibility: { g33: 0 },
              class_aggregates: {},
              economy: { gdp: 0, gini: 0, profit_rate: 0, exploitation_rate: 0 },
              predictions: { per_hyperedge: {} },
            },
          },
        }),
      ),
    );

    await useStore.getState().time.step(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("autopaused");
    expect(useStore.getState().time.autopauseEventIds).toEqual(["2-0"]);
  });

  it("resume() clears autopaused back to paused", async () => {
    useStore.getState().time.autopause(["e1"]);
    expect(useStore.getState().time.status).toBe("autopaused");

    useStore.getState().time.resume();

    expect(useStore.getState().time.status).toBe("paused");
    expect(useStore.getState().time.autopauseEventIds).toEqual([]);
  });
});

describe("time slice — play (serialized loop)", () => {
  it("plays ticks back-to-back with no overlapping resolves, then autopauses", async () => {
    // Tick 3's resolve response carries a critical event via the state fetch.
    let resolveCount = 0;
    server.use(
      http.post("/api/games/:id/resolve/", () => {
        resolveCount += 1;
        return HttpResponse.json({
          status: "ok",
          data: { resolved: true },
          tick: resolveCount + 1,
        });
      }),
      http.get("/api/games/:id/state/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            tick: resolveCount + 1,
            session_id: DEFAULT_GAME_ID,
            organizations: [],
            institutions: [],
            territories: [],
            hyperedges: [],
            edges: [],
            events:
              resolveCount >= 3 ? [makeEvent({ type: "rupture", tick: resolveCount + 1 })] : [],
            derived: {
              value_tensor: {
                departments: [],
                components: [],
                values: [],
                conservation_residual: 0,
              },
              imperial_rent: {
                unequal_exchange: 0,
                externalized_reproductive: 0,
                domestic_shadow: 0,
                total: 0,
              },
              dept_iii_visibility: { g33: 0 },
              class_aggregates: {},
              economy: { gdp: 0, gini: 0, profit_rate: 0, exploitation_rate: 0 },
              predictions: { per_hyperedge: {} },
            },
          },
        }),
      ),
    );

    await useStore.getState().time.play(DEFAULT_GAME_ID);

    // Stopped by the critical event on the 3rd resolve — never overshoots.
    expect(resolveCount).toBe(3);
    expect(useStore.getState().time.status).toBe("autopaused");

    // Requests strictly alternate resolve/state — never two resolves back
    // to back without an intervening state refetch (that would mean an
    // overlapping / unserialized loop).
    const resolveIdx = requestLog
      .map((r, i) => (r === "POST resolve" ? i : -1))
      .filter((i) => i >= 0);
    for (let i = 1; i < resolveIdx.length; i++) {
      const gapHasStateFetch = requestLog
        .slice(resolveIdx[i - 1]! + 1, resolveIdx[i])
        .includes("GET state");
      expect(gapHasStateFetch).toBe(true);
    }
  });

  it("play() is a no-op unless currently paused", async () => {
    // Default resolve handler never fires a critical event, so left
    // unbounded this loop would never stop on its own — pause() it
    // immediately so `first` settles deterministically.
    const first = useStore.getState().time.play(DEFAULT_GAME_ID);
    const secondAttemptStatus = useStore.getState().time.status;
    await useStore.getState().time.play(DEFAULT_GAME_ID); // no-op: not paused
    useStore.getState().time.pause();
    await first;

    expect(secondAttemptStatus).not.toBe("paused");
  });

  it("pause() requested mid-flight stops the loop after the in-flight resolve completes", async () => {
    let resolveCount = 0;
    server.use(
      http.post("/api/games/:id/resolve/", () => {
        resolveCount += 1;
        return HttpResponse.json({
          status: "ok",
          data: { resolved: true },
          tick: resolveCount + 1,
        });
      }),
    );

    const playPromise = useStore.getState().time.play(DEFAULT_GAME_ID);
    // Pause immediately — before the first resolve's promise settles.
    useStore.getState().time.pause();
    await playPromise;

    const stoppedAt = resolveCount;
    expect(useStore.getState().time.status).toBe("paused");

    // Give any (incorrect) further scheduling a chance to happen, then
    // confirm the loop really did stop.
    await new Promise((r) => setTimeout(r, 20));
    expect(resolveCount).toBe(stoppedAt);
  });
});

describe("time slice — spacebar", () => {
  it("paused -> dispatches play()", () => {
    const playSpy = vi.fn();
    useStore.setState((s) => ({ time: { ...s.time, status: "paused", play: playSpy } }));

    useStore.getState().time.toggleSpacebar(DEFAULT_GAME_ID);

    expect(playSpy).toHaveBeenCalledWith(DEFAULT_GAME_ID);
  });

  it("playing -> dispatches pause()", () => {
    const pauseSpy = vi.fn();
    useStore.setState((s) => ({ time: { ...s.time, status: "playing", pause: pauseSpy } }));

    useStore.getState().time.toggleSpacebar(DEFAULT_GAME_ID);

    expect(pauseSpy).toHaveBeenCalled();
  });

  it("does nothing while resolving/autopaused/error", () => {
    const playSpy = vi.fn();
    const pauseSpy = vi.fn();
    useStore.setState((s) => ({
      time: { ...s.time, status: "autopaused", play: playSpy, pause: pauseSpy },
    }));

    useStore.getState().time.toggleSpacebar(DEFAULT_GAME_ID);

    expect(playSpy).not.toHaveBeenCalled();
    expect(pauseSpy).not.toHaveBeenCalled();
  });
});

describe("time slice — speed (spec-113 architecture §4.1)", () => {
  it("defaults to speed 5 (zero injected delay — current behavior)", () => {
    expect(useStore.getState().time.speed).toBe(5);
  });

  it("setSpeed updates the speed field and is valid in any status", () => {
    useStore.getState().time.setSpeed(1);
    expect(useStore.getState().time.speed).toBe(1);

    useStore.setState((s) => ({ time: { ...s.time, status: "resolving" } }));
    useStore.getState().time.setSpeed(2);
    expect(useStore.getState().time.speed).toBe(2);
  });

  // These use real timers rather than vitest's fake timers deliberately:
  // `resolveOnce`'s loop races real `msw`-resolved promises against the
  // injected `setTimeout` delay, and fake-timer/real-promise interleaving
  // (`advanceTimersByTimeAsync` vs. an unbounded default mock resolver that
  // always returns "ok") proved to under-flush the promise chain and hang
  // the loop. A short real 800ms delay keeps these tests fast and safe.

  it("at speed 1, injects a real inter-resolve delay before the next resolve fires", async () => {
    useStore.getState().time.setSpeed(1); // 800ms delay
    const playPromise = useStore.getState().time.play(DEFAULT_GAME_ID);

    await new Promise((r) => setTimeout(r, 50)); // first resolve + refetch should have landed
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);

    await new Promise((r) => setTimeout(r, 300)); // still well inside the 800ms delay
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);

    useStore.getState().time.pause();
    await playPromise;
  });

  it("pause() requested during the injected delay stops the loop before the next resolve fires", async () => {
    useStore.getState().time.setSpeed(1); // 800ms delay
    const playPromise = useStore.getState().time.play(DEFAULT_GAME_ID);

    await new Promise((r) => setTimeout(r, 50)); // first resolve + refetch lands
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);

    useStore.getState().time.pause(); // fired while inside the 800ms delay
    await playPromise;

    // No second resolve was ever scheduled — pause() during the delay wins.
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);
    expect(useStore.getState().time.status).toBe("paused");

    // Give any (incorrect) further scheduling a chance to happen.
    await new Promise((r) => setTimeout(r, 900));
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);
  });

  it("a speed change mid-loop applies to the very next delay, not the in-flight one", async () => {
    useStore.getState().time.setSpeed(1); // 800ms delay
    const playPromise = useStore.getState().time.play(DEFAULT_GAME_ID);

    await new Promise((r) => setTimeout(r, 50)); // first resolve lands, now inside delay #1
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);

    useStore.getState().time.setSpeed(5); // must NOT shorten the in-flight delay
    await new Promise((r) => setTimeout(r, 300));
    expect(requestLog.filter((r) => r === "POST resolve")).toHaveLength(1);

    // Let delay #1 (800ms total) finish — resolve #2 fires, and its own
    // delay is now 0ms (5x), so the loop races ahead; stop it and confirm
    // it did advance past a single resolve.
    await new Promise((r) => setTimeout(r, 550));
    useStore.getState().time.pause();
    await playPromise;

    expect(requestLog.filter((r) => r === "POST resolve").length).toBeGreaterThanOrEqual(2);
  });

  it("autopause still fires with no delay involved regardless of speed", async () => {
    server.use(
      http.post("/api/games/:id/resolve/", () =>
        HttpResponse.json({ status: "ok", data: { resolved: true }, tick: 2 }),
      ),
      http.get("/api/games/:id/state/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            tick: 2,
            session_id: DEFAULT_GAME_ID,
            organizations: [],
            institutions: [],
            territories: [],
            hyperedges: [],
            edges: [],
            events: [makeEvent({ type: "rupture", tick: 2 })],
            derived: {
              value_tensor: {
                departments: [],
                components: [],
                values: [],
                conservation_residual: 0,
              },
              imperial_rent: {
                unequal_exchange: 0,
                externalized_reproductive: 0,
                domestic_shadow: 0,
                total: 0,
              },
              dept_iii_visibility: { g33: 0 },
              class_aggregates: {},
              economy: { gdp: 0, gini: 0, profit_rate: 0, exploitation_rate: 0 },
              predictions: { per_hyperedge: {} },
            },
          },
        }),
      ),
    );

    useStore.getState().time.setSpeed(1);
    await useStore.getState().time.step(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("autopaused");
    expect(useStore.getState().time.autopauseEventIds).toEqual(["2-0"]);
  });
});
