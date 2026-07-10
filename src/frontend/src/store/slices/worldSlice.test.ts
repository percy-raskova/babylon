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

  it("autopauses the time slice when the newly-observed tick carries a critical event", async () => {
    resetMockGameState({ events: [makeEvent({ type: "rupture", tick: 2 })] });

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("autopaused");
    expect(useStore.getState().time.autopauseEventIds).toEqual(["2-0"]);
  });

  it("does not autopause on non-critical events", async () => {
    resetMockGameState({ events: [makeEvent({ type: "consciousness_shift", tick: 1 })] });

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID);

    expect(useStore.getState().time.status).toBe("paused");
  });
});
