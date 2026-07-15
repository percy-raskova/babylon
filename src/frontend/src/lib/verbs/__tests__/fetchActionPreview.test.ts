/**
 * Red-first tests for `fetchActionPreview` — the store-free live fetch
 * behind the VerbForm preview strip (Program 17 Wave 1 item W1.2), replacing
 * the fake constant-direction chips. Mirrors `fetchVerbTargets.test.ts`'s
 * shape; unlike the per-verb target endpoints, `/actions/preview/` returns
 * the standard {status, data, tick, session_id} envelope, so there is no
 * flat-body quirk to unwrap here.
 */

import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { fetchActionPreview } from "../fetchActionPreview";

const PREVIEW_PAYLOAD = {
  estimated_consciousness_delta: 0.02,
  estimated_heat_delta: 0,
  action_point_cost: 1,
  success_probability: 0.75,
  affected_territory_ids: ["t-1"],
  warnings: [],
};

describe("fetchActionPreview", () => {
  it("returns ok:true with the unwrapped preview payload", async () => {
    server.use(
      http.post("/api/games/game-001/actions/preview/", () =>
        HttpResponse.json({ status: "ok", tick: 5, session_id: "game-001", data: PREVIEW_PAYLOAD }),
      ),
    );

    const result = await fetchActionPreview("game-001", "org-1", "educate", "t-1");

    expect(result.ok).toBe(true);
    expect(result.data).toEqual(PREVIEW_PAYLOAD);
  });

  it("posts org_id, verb, and target_id in the request body", async () => {
    let capturedBody: unknown;
    server.use(
      http.post("/api/games/game-001/actions/preview/", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ status: "ok", data: PREVIEW_PAYLOAD });
      }),
    );

    await fetchActionPreview("game-001", "org-2", "attack", "target-9");

    expect(capturedBody).toEqual({ org_id: "org-2", verb: "attack", target_id: "target-9" });
  });

  it("sends target_id: null when no target is selected", async () => {
    let capturedBody: unknown;
    server.use(
      http.post("/api/games/game-001/actions/preview/", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ status: "ok", data: PREVIEW_PAYLOAD });
      }),
    );

    await fetchActionPreview("game-001", "org-2", "reproduce");

    expect(capturedBody).toEqual({ org_id: "org-2", verb: "reproduce", target_id: null });
  });

  it("requests the game's preview endpoint", async () => {
    let capturedUrl = "";
    server.use(
      http.post("/api/games/game-042/actions/preview/", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ status: "ok", data: PREVIEW_PAYLOAD });
      }),
    );

    await fetchActionPreview("game-042", "org-1", "educate", "t-1");

    expect(capturedUrl).toContain("/api/games/game-042/actions/preview/");
  });

  it("returns ok:false with a message on a server error", async () => {
    server.use(
      http.post("/api/games/game-001/actions/preview/", () =>
        HttpResponse.json({ status: "error", data: null, message: "boom" }, { status: 500 }),
      ),
    );

    const result = await fetchActionPreview("game-001", "org-1", "educate", "t-1");

    expect(result.ok).toBe(false);
    expect(result.data).toBeNull();
    expect(result.message).toBeTruthy();
  });
});
