/**
 * Contract tests for the map-replay slice (Program 17 Wave 3, Frontend-W3R3
 * "RADAR LOOP" tick scrubber) — TDD red phase written before the
 * implementation. Mirrors `mapSlice.test.ts`'s idiom: `resetStore()` +
 * `resetMockGameState()` in `beforeEach`, `server.use()` for scripted
 * responses, `requestLog`/`DEFAULT_GAME_ID` from `test/handlers.ts`.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeMapHistoryPayload, makeMapHistoryFrame } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

/** Enter replay with `count` synthetic frames (ticks 0..count-1) — shared by the scrubTo/step bounds suites below. */
async function enterWithFrameCount(count: number): Promise<void> {
  server.use(
    http.get("/api/games/:id/map/history/", () =>
      HttpResponse.json({
        status: "ok",
        data: makeMapHistoryPayload({
          frames: Array.from({ length: count }, (_, i) => makeMapHistoryFrame({ tick: i })),
        }),
      }),
    ),
  );
  await useStore.getState().mapReplay.enter(DEFAULT_GAME_ID, "heat");
}

describe("mapReplay slice — initial state", () => {
  it("starts idle/inactive with an empty window", () => {
    const { mapReplay } = useStore.getState();
    expect(mapReplay.active).toBe(false);
    expect(mapReplay.metric).toBeNull();
    expect(mapReplay.frames).toEqual([]);
    expect(mapReplay.currentIndex).toBe(0);
    expect(mapReplay.capped).toBe(false);
    expect(mapReplay.status).toBe("idle");
    expect(mapReplay.error).toBeNull();
    expect(mapReplay.liveTickAvailable).toBeNull();
  });
});

describe("mapReplay slice — enter", () => {
  it("fetches the window, marks active/ready, and defaults the scrubber to the latest frame", async () => {
    server.use(
      http.get("/api/games/:id/map/history/", () => {
        requestLog.push("GET map:history");
        return HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({
            metric: "heat",
            from_tick: 3,
            to_tick: 5,
            capped: false,
            frames: [
              makeMapHistoryFrame({ tick: 3, values: { "26163": 0.1 } }),
              makeMapHistoryFrame({ tick: 4, values: { "26163": 0.2 } }),
              makeMapHistoryFrame({ tick: 5, values: { "26163": 0.3 } }),
            ],
          }),
        });
      }),
    );

    await useStore.getState().mapReplay.enter(DEFAULT_GAME_ID, "heat");

    const { mapReplay } = useStore.getState();
    expect(mapReplay.active).toBe(true);
    expect(mapReplay.status).toBe("ready");
    expect(mapReplay.metric).toBe("heat");
    expect(mapReplay.frames).toHaveLength(3);
    expect(mapReplay.currentIndex).toBe(2);
    expect(mapReplay.capped).toBe(false);
    expect(mapReplay.error).toBeNull();
    expect(requestLog.filter((r) => r === "GET map:history")).toHaveLength(1);
  });

  it("carries the capped flag through from the response", async () => {
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({
            capped: true,
            frames: [makeMapHistoryFrame({ tick: 100 })],
          }),
        }),
      ),
    );

    await useStore.getState().mapReplay.enter(DEFAULT_GAME_ID, "population");
    expect(useStore.getState().mapReplay.capped).toBe(true);
  });

  it("an honest empty window (no frames) is 'ready' with an empty frames array, not an error", async () => {
    // Default handler serves frames: [] — see test/handlers.ts.
    await useStore.getState().mapReplay.enter(DEFAULT_GAME_ID, "profit_rate");
    const { mapReplay } = useStore.getState();
    expect(mapReplay.status).toBe("ready");
    expect(mapReplay.frames).toEqual([]);
    expect(mapReplay.currentIndex).toBe(0);
    expect(mapReplay.error).toBeNull();
  });

  it("a failed fetch (e.g. 422 not_replayable) lands in the 'error' status with an honest message, frames empty", async () => {
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json(
          { status: "error", message: "Metric 'occ' has no persisted per-tick history" },
          { status: 422 },
        ),
      ),
    );

    await useStore.getState().mapReplay.enter(DEFAULT_GAME_ID, "exploitation_rate");

    const { mapReplay } = useStore.getState();
    expect(mapReplay.status).toBe("error");
    expect(mapReplay.error).toContain("no persisted per-tick history");
    expect(mapReplay.frames).toEqual([]);
    // Still marked active — the panel stays open showing the error, rather
    // than silently reverting to the pre-enter "start replay" prompt.
    expect(mapReplay.active).toBe(true);
  });
});

describe("mapReplay slice — exit", () => {
  it("resets every state field back to idle/inactive, but preserves the action references", async () => {
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({
            frames: [makeMapHistoryFrame({ tick: 1 }), makeMapHistoryFrame({ tick: 2 })],
          }),
        }),
      ),
    );
    await useStore.getState().mapReplay.enter(DEFAULT_GAME_ID, "heat");
    expect(useStore.getState().mapReplay.active).toBe(true);
    const enterRef = useStore.getState().mapReplay.enter;

    useStore.getState().mapReplay.exit();

    const { mapReplay } = useStore.getState();
    expect(mapReplay.active).toBe(false);
    expect(mapReplay.metric).toBeNull();
    expect(mapReplay.frames).toEqual([]);
    expect(mapReplay.currentIndex).toBe(0);
    expect(mapReplay.capped).toBe(false);
    expect(mapReplay.status).toBe("idle");
    expect(mapReplay.error).toBeNull();
    expect(mapReplay.liveTickAvailable).toBeNull();
    // No residual state (frame invariance) AND the action itself survives
    // the reset (panelFactory.createPanel's same "methods stay stable"
    // contract).
    expect(mapReplay.enter).toBe(enterRef);
  });
});

describe("mapReplay slice — scrubTo bounds", () => {
  it("clamps an out-of-range high index to the last frame", async () => {
    await enterWithFrameCount(5);
    useStore.getState().mapReplay.scrubTo(999);
    expect(useStore.getState().mapReplay.currentIndex).toBe(4);
  });

  it("clamps a negative index to 0", async () => {
    await enterWithFrameCount(5);
    useStore.getState().mapReplay.scrubTo(-5);
    expect(useStore.getState().mapReplay.currentIndex).toBe(0);
  });

  it("accepts an in-range index unchanged", async () => {
    await enterWithFrameCount(5);
    useStore.getState().mapReplay.scrubTo(2);
    expect(useStore.getState().mapReplay.currentIndex).toBe(2);
  });

  it("clamps to 0 on an empty frame set", async () => {
    await enterWithFrameCount(0);
    useStore.getState().mapReplay.scrubTo(3);
    expect(useStore.getState().mapReplay.currentIndex).toBe(0);
  });
});

describe("mapReplay slice — step bounds", () => {
  it("steps forward by one", async () => {
    await enterWithFrameCount(5);
    useStore.getState().mapReplay.scrubTo(1);
    useStore.getState().mapReplay.step(1);
    expect(useStore.getState().mapReplay.currentIndex).toBe(2);
  });

  it("steps backward by one", async () => {
    await enterWithFrameCount(5);
    useStore.getState().mapReplay.scrubTo(3);
    useStore.getState().mapReplay.step(-1);
    expect(useStore.getState().mapReplay.currentIndex).toBe(2);
  });

  it("stepping forward past the last frame stays clamped at the last index", async () => {
    await enterWithFrameCount(3);
    useStore.getState().mapReplay.scrubTo(2);
    useStore.getState().mapReplay.step(1);
    expect(useStore.getState().mapReplay.currentIndex).toBe(2);
  });

  it("stepping backward past the first frame stays clamped at 0", async () => {
    await enterWithFrameCount(3);
    useStore.getState().mapReplay.scrubTo(0);
    useStore.getState().mapReplay.step(-1);
    expect(useStore.getState().mapReplay.currentIndex).toBe(0);
  });
});

describe("mapReplay slice — noteLiveTick", () => {
  async function enterWithFrameTicks(ticks: number[]): Promise<void> {
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({
            frames: ticks.map((tick) => makeMapHistoryFrame({ tick })),
          }),
        }),
      ),
    );
    await useStore.getState().mapReplay.enter(DEFAULT_GAME_ID, "heat");
  }

  it("sets liveTickAvailable when a newer tick than the fetched window's last frame arrives while active", async () => {
    await enterWithFrameTicks([1, 2, 3]);
    useStore.getState().mapReplay.noteLiveTick(4);
    expect(useStore.getState().mapReplay.liveTickAvailable).toBe(4);
  });

  it("does not set liveTickAvailable for a tick already inside the fetched window", async () => {
    await enterWithFrameTicks([1, 2, 3]);
    useStore.getState().mapReplay.noteLiveTick(3);
    expect(useStore.getState().mapReplay.liveTickAvailable).toBeNull();
  });

  it("is a no-op while replay is inactive", () => {
    useStore.getState().mapReplay.noteLiveTick(10);
    expect(useStore.getState().mapReplay.liveTickAvailable).toBeNull();
  });

  it("clears back to null once the noted tick is no longer newer (e.g. after re-entering with a fresher window)", async () => {
    await enterWithFrameTicks([1, 2, 3]);
    useStore.getState().mapReplay.noteLiveTick(5);
    expect(useStore.getState().mapReplay.liveTickAvailable).toBe(5);

    useStore.getState().mapReplay.noteLiveTick(3);
    expect(useStore.getState().mapReplay.liveTickAvailable).toBeNull();
  });
});
