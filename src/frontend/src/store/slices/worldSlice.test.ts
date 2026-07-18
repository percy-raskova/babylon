/**
 * Contract tests for the world slice (spec-110 B3) — `fetchState` and its
 * `onTickAdvanced` fan-out: exactly one refetch per *mounted* panel per
 * observed tick change, plus autopausing `time` on a critical event.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID, setMockSnapshot } from "@/test/handlers";
import { makeEvent } from "@/test/fixtures";
import { PANEL_KEYS } from "@/store/slices/panels";
import type { GameSnapshot } from "@/types/game";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("world slice — fetchState", () => {
  it("populates the snapshot and lastTick on success", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    const { snapshot, lastTick, loading, error } = useStore.getState().world;
    expect(loading).toBe(false);
    expect(error).toBeNull();
    expect(snapshot).not.toBeNull();
    expect(lastTick).toBe(snapshot?.tick);
  });

  it("fans out exactly one fetch per mounted panel on the first observed tick", async () => {
    useStore.getState().panels.summary.setMounted(true);
    useStore.getState().panels.economy.setMounted(true);
    // timeseries/communities/map left unmounted on purpose.

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(requestLog.filter((r) => r === "GET summary")).toHaveLength(1);
    expect(requestLog.filter((r) => r === "GET economy")).toHaveLength(1);
    expect(requestLog.filter((r) => r === "GET timeseries")).toHaveLength(0);
    expect(requestLog.filter((r) => r === "GET communities")).toHaveLength(0);
    expect(requestLog.filter((r) => r === "GET map")).toHaveLength(0);
  });

  it("does not re-fan-out when the tick has not changed", async () => {
    useStore.getState().panels.summary.setMounted(true);
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const afterFirst = requestLog.filter((r) => r === "GET summary").length;
    expect(afterFirst).toBe(1);

    // Same tick — heartbeat-style refetch with no engine-side change.
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(requestLog.filter((r) => r === "GET summary")).toHaveLength(afterFirst);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(2);
  });

  it("keeps the same snapshot object reference across two fetches of an identical same-tick payload", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const first = useStore.getState().world.snapshot;
    expect(first).not.toBeNull();

    // Same tick, byte-identical content — heartbeat-style refetch with no
    // engine-side change. `world` itself is a new object every fetch
    // (loading toggles legitimately churn it) — only `snapshot` must stay
    // referentially stable so DeckGLMap's memoized layers don't rebuild.
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const second = useStore.getState().world.snapshot;

    expect(Object.is(first, second)).toBe(true);
  });

  it("takes a new snapshot reference when a same-tick payload actually changed", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const first = useStore.getState().world.snapshot!;

    const changedHeat = first.territories[0]!.heat + 0.5;
    const changed: GameSnapshot = {
      ...first,
      territories: first.territories.map((t, i) => (i === 0 ? { ...t, heat: changedHeat } : t)),
    };
    setMockSnapshot(changed);

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const second = useStore.getState().world.snapshot;

    // The guard against swallowing same-tick server-side changes: an
    // actual content change must NEVER be mistaken for a duplicate beat.
    expect(Object.is(first, second)).toBe(false);
    expect(second!.territories[0]!.heat).toBe(changedHeat);
  });

  it("takes a new snapshot reference when the tick has advanced", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const first = useStore.getState().world.snapshot!;

    setMockSnapshot({ ...first, tick: first.tick + 1 });

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const second = useStore.getState().world.snapshot;

    expect(Object.is(first, second)).toBe(false);
    expect(second!.tick).toBe(first.tick + 1);
  });

  it("fans out to every mounted panel again once the tick advances", async () => {
    useStore.getState().panels.summary.setMounted(true);
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    expect(requestLog.filter((r) => r === "GET summary")).toHaveLength(1);

    await useStore.getState().time.step(DEFAULT_GAME_ID); // advances the mock tick

    expect(requestLog.filter((r) => r === "GET summary")).toHaveLength(2);
  });

  it("never fetches an unmounted panel", async () => {
    // Nothing mounted at all.
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    const panelLabels = new Set(PANEL_KEYS.map((key) => `GET ${key}`));
    expect(requestLog.filter((r) => panelLabels.has(r))).toEqual([]);
  });

  it("surfaces a backend error without touching the previous snapshot", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const firstSnapshot = useStore.getState().world.snapshot;

    server.use(
      http.get("/api/games/:id/state/", () =>
        HttpResponse.json({ status: "error", message: "boom" }, { status: 500 }),
      ),
    );

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().world.error).toBe("boom");
    expect(useStore.getState().world.snapshot).toBe(firstSnapshot);
  });

  it("autopauses the time slice with dedup keys when the newly-observed tick carries a critical event", async () => {
    resetMockGameState({ events: [makeEvent({ type: "endgame_reached", tick: 2, data: {} })] });

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("autopaused");
    expect(useStore.getState().time.autopauseEventKeys).toEqual(["endgame_reached:global"]);
    expect(useStore.getState().events.acknowledgedAutopauseKeys).toEqual([
      "endgame_reached:global@2",
    ]);
  });

  it("does not autopause on non-critical events", async () => {
    resetMockGameState({ events: [makeEvent({ type: "consciousness_shift", tick: 1 })] });

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("paused");
  });

  it("ingests the tick's events into the events slice on every observed tick", async () => {
    resetMockGameState({ events: [makeEvent({ type: "uprising", tick: 1 })] });

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().events.ingestedTicks).toEqual([1]);
    expect(useStore.getState().events.toasts).toHaveLength(1);
  });
});

describe("world slice — autopause-once (spec-116 FR-116-2 iii)", () => {
  it("does not re-autopause when the same tick is re-observed after a reload-style reset", async () => {
    resetMockGameState({ events: [makeEvent({ type: "endgame_reached", tick: 2, data: {} })] });
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    useStore.getState().time.resume();

    // Reload: the world slice loses its tick memory; the session-scoped
    // acknowledged set does not (same store instance, same session). This is
    // the real autopause-once guard — it fails if the acknowledged set is
    // not consulted or does not persist across the world-slice reset.
    useStore.setState((s) => ({ world: { ...s.world, snapshot: null, lastTick: null } }));
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("paused");
  });

  it("two concurrent fetches of the same tick autopause exactly once (fetchState serializes the advance)", async () => {
    resetMockGameState({ events: [makeEvent({ type: "endgame_reached", tick: 2, data: {} })] });

    await Promise.all([
      useStore.getState().world.fetchState(DEFAULT_GAME_ID),
      useStore.getState().world.fetchState(DEFAULT_GAME_ID),
    ]);

    // fetchState reads-then-writes `lastTick` atomically (no await between),
    // so only the first racer's tick-guard passes and reaches onTickAdvanced;
    // the second sees the advanced tick and skips it. Result: exactly one
    // advance, one acknowledgement, and a single resume that STICKS. (The
    // acknowledged-set re-observation guard is the reload-reset test above;
    // this pins the serialization that stops concurrent fetches double-firing.)
    expect(useStore.getState().time.status).toBe("autopaused");
    useStore.getState().time.resume();
    expect(useStore.getState().time.status).toBe("paused");
    expect(
      useStore
        .getState()
        .events.acknowledgedAutopauseKeys.filter((k) => k === "endgame_reached:global@2"),
    ).toHaveLength(1);
  });

  it("a NEW endgame occurrence on a later tick still autopauses (always-autopause)", async () => {
    resetMockGameState({ events: [makeEvent({ type: "endgame_reached", tick: 2, data: {} })] });
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    useStore.getState().time.resume();

    setMockSnapshot({
      ...useStore.getState().world.snapshot!,
      tick: 3,
      events: [makeEvent({ type: "endgame_reached", tick: 3, data: {} })],
    });
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("autopaused");
  });
});

describe("world slice — endgame auto-open (spec-113 §4.4 correction)", () => {
  it("opens the chronicle takeover + pauses exactly once when outcome transitions null -> non-null", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID); // outcome still null

    expect(useStore.getState().ui.takeover.active).toBeNull();
    expect(requestLog.filter((r) => r === "GET endgame")).toHaveLength(1);

    server.use(
      http.get("/api/games/:id/endgame/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            tick: 2,
            outcome: "revolutionary_victory",
            headline: "The masses have won.",
            summary: "",
            stats: { final_tick: 2, consciousness: 0.9, solidarity_edges: 10, heat: 0.1 },
          },
        }),
      ),
    );

    setMockSnapshot({ ...useStore.getState().world.snapshot!, tick: 2 });
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().ui.takeover.active).toBe("chronicle");
    expect(useStore.getState().time.status).toBe("paused");

    // A further observed tick with the outcome still non-null must not
    // re-open/re-pause — the transition already fired once.
    useStore.getState().ui.closeTakeover();
    setMockSnapshot({ ...useStore.getState().world.snapshot!, tick: 3 });
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().ui.takeover.active).toBeNull();
  });

  it("does not open the chronicle takeover while outcome stays null", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    setMockSnapshot({ ...useStore.getState().world.snapshot!, tick: 2 });
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().ui.takeover.active).toBeNull();
  });
});

describe("world slice — acceptOutcome (spec-116 FR-116-5 mercy affordance)", () => {
  const LOCKED_ENDGAME_RESPONSE = {
    status: "ok" as const,
    data: {
      tick: 3,
      outcome: "fascist_consolidation",
      headline: "False consciousness has consolidated the state.",
      summary: "",
      stats: { final_tick: 3, consciousness: 0.2, solidarity_edges: 1, heat: 0.5 },
    },
  };

  it("POSTs accept-outcome then refetches the endgame panel", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const endgameCallsBefore = requestLog.filter((r) => r === "GET endgame").length;

    server.use(
      http.post("/api/games/:id/accept-outcome/", () => {
        requestLog.push("POST accept-outcome");
        return HttpResponse.json({
          status: "ok",
          data: { outcome: "fascist_consolidation", tick: 3, accepted: true },
        });
      }),
      http.get("/api/games/:id/endgame/", () => {
        requestLog.push("GET endgame");
        return HttpResponse.json(LOCKED_ENDGAME_RESPONSE);
      }),
    );

    await useStore.getState().world.acceptOutcome(DEFAULT_GAME_ID);

    expect(requestLog.filter((r) => r === "POST accept-outcome")).toHaveLength(1);
    expect(requestLog.filter((r) => r === "GET endgame")).toHaveLength(endgameCallsBefore + 1);
  });

  it("opens the chronicle takeover + pauses when the outcome transitions null -> non-null", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    expect(useStore.getState().ui.takeover.active).toBeNull();

    server.use(
      http.post("/api/games/:id/accept-outcome/", () =>
        HttpResponse.json({
          status: "ok",
          data: { outcome: "fascist_consolidation", tick: 3, accepted: true },
        }),
      ),
      http.get("/api/games/:id/endgame/", () => HttpResponse.json(LOCKED_ENDGAME_RESPONSE)),
    );

    await useStore.getState().world.acceptOutcome(DEFAULT_GAME_ID);

    expect(useStore.getState().ui.takeover.active).toBe("chronicle");
    expect(useStore.getState().time.status).toBe("paused");
  });

  it("does not refetch the endgame panel or open the takeover when the POST fails", async () => {
    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);
    const endgameCallsBefore = requestLog.filter((r) => r === "GET endgame").length;

    server.use(
      http.post("/api/games/:id/accept-outcome/", () =>
        HttpResponse.json({ status: "error", message: "outcome not locked" }, { status: 400 }),
      ),
    );

    await useStore.getState().world.acceptOutcome(DEFAULT_GAME_ID);

    expect(requestLog.filter((r) => r === "GET endgame")).toHaveLength(endgameCallsBefore);
    expect(useStore.getState().ui.takeover.active).toBeNull();
  });
});
