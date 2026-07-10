/**
 * Red-first tests for `fetchVerbTargets` — the store-free lib extraction of
 * `web/frontend/src/stores/gameStore.ts`'s `fetchVerbTargets` action
 * (spec-110 B2). Caching/store-set behavior is B3's job (the zustand store
 * that wraps this call); this module is the pure fetch-and-normalize half.
 */

import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { fetchVerbTargets } from "../fetchVerbTargets";

describe("fetchVerbTargets", () => {
  it("returns ok:true with the flat body when the endpoint has no status envelope (mobilize-style)", async () => {
    server.use(
      http.get("/api/games/game-001/actions/mobilize/targets/", () =>
        HttpResponse.json({ targets: [{ id: "m-1", name: "Rally" }] }),
      ),
    );

    const result = await fetchVerbTargets("game-001", "mobilize", "org-1");

    expect(result.ok).toBe(true);
    expect(result.payload).toEqual({ targets: [{ id: "m-1", name: "Rally" }] });
  });

  it("unwraps the standard {status, data} envelope when present (educate-style)", async () => {
    server.use(
      http.get("/api/games/game-001/actions/educate/targets/", () =>
        HttpResponse.json({
          status: "ok",
          data: { targets: [{ community_id: "comm-1" }] },
        }),
      ),
    );

    const result = await fetchVerbTargets("game-001", "educate", "org-1");

    expect(result.ok).toBe(true);
    expect(result.payload).toEqual({ targets: [{ community_id: "comm-1" }] });
  });

  it("requests the per-verb endpoint with the org_id query param", async () => {
    let capturedUrl = "";
    server.use(
      http.get("/api/games/game-001/actions/attack/targets/", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ targets: [] });
      }),
    );

    await fetchVerbTargets("game-001", "attack", "org-2");

    expect(capturedUrl).toContain("/api/games/game-001/actions/attack/targets/");
    expect(capturedUrl).toContain("org_id=org-2");
  });

  it("returns ok:false with a message on a server error", async () => {
    server.use(
      http.get("/api/games/game-001/actions/attack/targets/", () =>
        HttpResponse.json({ status: "error", data: null, message: "boom" }, { status: 500 }),
      ),
    );

    const result = await fetchVerbTargets("game-001", "attack", "org-2");

    expect(result.ok).toBe(false);
    expect(result.payload).toEqual({});
    expect(result.message).toBeTruthy();
  });
});
