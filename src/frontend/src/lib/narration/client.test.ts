/**
 * Red-first tests for `fetchNarration` — the store-free client for the
 * narration endpoint (real since program-20 B5: `web/game/api.py::game_narration`).
 * See `client.ts` for the documented request/response contract.
 */

import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { fetchNarration } from "./client";
import type { NarrationBeat } from "@/types/narration";

const BEAT: NarrationBeat = {
  id: "beat-1",
  tick: 104,
  scope: "event",
  subjectRef: "evt-1",
  headline: "Federal agents raided the WCLF hall, tick 104.",
  body: "Federal agents breached the WCLF hall on Schaefer before dawn.",
  register: "wire",
};

describe("fetchNarration", () => {
  it("returns ready status with beats on a normal 200", async () => {
    server.use(
      http.get("/api/games/game-001/narration/", () =>
        HttpResponse.json({ status: "ok", data: { status: "ready", beats: [BEAT] } }),
      ),
    );

    const result = await fetchNarration("game-001");

    expect(result).toEqual({ status: "ready", beats: [BEAT] });
  });

  it("passes through a pending status with no beats", async () => {
    server.use(
      http.get("/api/games/game-001/narration/", () =>
        HttpResponse.json({ status: "ok", data: { status: "pending", beats: [] } }),
      ),
    );

    const result = await fetchNarration("game-001");

    expect(result).toEqual({ status: "pending", beats: [] });
  });

  it("degrades a 404 (endpoint not implemented yet) to offline with no beats", async () => {
    server.use(
      http.get("/api/games/game-001/narration/", () =>
        HttpResponse.json({ status: "error", message: "Not Found" }, { status: 404 }),
      ),
    );

    const result = await fetchNarration("game-001");

    expect(result).toEqual({ status: "offline", beats: [] });
  });

  it("degrades any other server error to offline as well (never throws, never fabricates ready)", async () => {
    server.use(
      http.get("/api/games/game-001/narration/", () =>
        HttpResponse.json({ status: "error", message: "boom" }, { status: 500 }),
      ),
    );

    const result = await fetchNarration("game-001");

    expect(result).toEqual({ status: "offline", beats: [] });
  });

  it("degrades a network error to offline", async () => {
    server.use(http.get("/api/games/game-001/narration/", () => HttpResponse.error()));

    const result = await fetchNarration("game-001");

    expect(result).toEqual({ status: "offline", beats: [] });
  });

  it("includes since_tick in the query string when provided", async () => {
    let capturedUrl = "";
    server.use(
      http.get("/api/games/game-001/narration/", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ status: "ok", data: { status: "ready", beats: [] } });
      }),
    );

    await fetchNarration("game-001", 100);

    expect(capturedUrl).toContain("since_tick=100");
  });

  it("omits since_tick from the query string when not provided", async () => {
    let capturedUrl = "";
    server.use(
      http.get("/api/games/game-001/narration/", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ status: "ok", data: { status: "ready", beats: [] } });
      }),
    );

    await fetchNarration("game-001");

    expect(capturedUrl).not.toContain("since_tick");
  });
});
