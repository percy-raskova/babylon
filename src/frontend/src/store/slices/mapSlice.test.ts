/**
 * Contract tests for the map slice (spec-110 B3) — Lens/framing/viewport
 * controls, and the selection-change -> inspector fan-out.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("map slice — view controls", () => {
  it("defaults to the stance lens, hex framing, no selection, no faction filter", () => {
    // The rendered default stays identical to today (spec-112 C5): county
    // framing used to BE the default, but nothing ever drew aggregated
    // regions, so the map always rendered hex tiles regardless. Now that
    // county framing actually renders, "hex" is the explicit default.
    const { map } = useStore.getState();
    expect(map.lens).toEqual({ kind: "stance" });
    expect(map.framing).toBe("hex");
    expect(map.viewportBbox).toBeNull();
    expect(map.selection).toBeNull();
    expect(map.factionFilter).toBeNull();
  });

  it("setLens/setFraming/setViewportBbox update independently", () => {
    useStore.getState().map.setLens({ kind: "heat" });
    useStore.getState().map.setFraming("county");
    useStore.getState().map.setViewportBbox([-84, 42, -83, 43]);

    const { map } = useStore.getState();
    expect(map.lens).toEqual({ kind: "heat" });
    expect(map.framing).toBe("county");
    expect(map.viewportBbox).toEqual([-84, 42, -83, 43]);
  });

  it("setFactionFilter sets and clears the faction filter", () => {
    useStore.getState().map.setFactionFilter("FAC_DECOLONIAL");
    expect(useStore.getState().map.factionFilter).toBe("FAC_DECOLONIAL");
    useStore.getState().map.setFactionFilter(null);
    expect(useStore.getState().map.factionFilter).toBeNull();
  });
});

describe("map slice — setFraming fans out a map fetch", () => {
  it("updates framing but fetches nothing when no active game is set", async () => {
    useStore.getState().map.setFraming("county");
    await new Promise((r) => setTimeout(r, 0));

    expect(useStore.getState().map.framing).toBe("county");
    expect(requestLog.filter((r) => r === "GET map")).toHaveLength(0);
  });

  it("fans out exactly one panels.map fetch whose URL carries the new zoom once a game is active", async () => {
    let capturedUrl = "";
    server.use(
      http.get("/api/games/:id/map/", ({ request }) => {
        requestLog.push("GET map");
        capturedUrl = request.url;
        return HttpResponse.json({
          status: "ok",
          data: { type: "FeatureCollection", features: [] },
        });
      }),
    );
    useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);

    useStore.getState().map.setFraming("county");
    await new Promise((r) => setTimeout(r, 0));

    expect(useStore.getState().map.framing).toBe("county");
    expect(requestLog.filter((r) => r === "GET map")).toHaveLength(1);
    expect(capturedUrl).toContain("zoom=county");
  });
});

describe("map slice — selection fans out an inspector fetch", () => {
  it("does nothing when no active game is set", () => {
    useStore.getState().map.setSelection({ kind: "hex", id: "h1" });

    expect(useStore.getState().map.selection).toEqual({ kind: "hex", id: "h1" });
    expect(requestLog.filter((r) => r.startsWith("GET inspector"))).toHaveLength(0);
  });

  it("fetches the inspector endpoint for the selection kind/id once a game is active", async () => {
    useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);

    useStore.getState().map.setSelection({ kind: "org", id: "org-1" });
    // fetchForSelection is fired-and-forgotten by setSelection; wait a tick.
    await new Promise((r) => setTimeout(r, 0));

    expect(requestLog.filter((r) => r === "GET inspector:org")).toHaveLength(1);
    expect(useStore.getState().panels.inspector.data).toEqual({ kind: "org", id: "org-1" });
  });

  it("clearing the selection (null) clears inspector data without a fetch", async () => {
    useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);
    useStore.getState().map.setSelection({ kind: "hex", id: "h1" });
    await new Promise((r) => setTimeout(r, 0));
    expect(useStore.getState().panels.inspector.data).not.toBeNull();

    useStore.getState().map.setSelection(null);

    expect(useStore.getState().map.selection).toBeNull();
    expect(useStore.getState().panels.inspector.data).toBeNull();
  });

  it("a later selection wins over a slower earlier one (stale-response guard)", async () => {
    let resolveFirst: (() => void) | undefined;
    server.use(
      http.get("/api/games/:id/node/:entityId/", async () => {
        await new Promise<void>((r) => {
          resolveFirst = r;
        });
        return HttpResponse.json({ status: "ok", data: { kind: "node", id: "slow" } });
      }),
      http.get("/api/games/:id/org/:entityId/", () =>
        HttpResponse.json({ status: "ok", data: { kind: "org", id: "fast" } }),
      ),
    );
    useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);

    const slow = useStore
      .getState()
      .panels.inspector.fetchForSelection(DEFAULT_GAME_ID, "node", "n1");
    useStore.getState().map.setSelection({ kind: "org", id: "fast" });
    await new Promise((r) => setTimeout(r, 0));
    expect(useStore.getState().panels.inspector.data).toEqual({ kind: "org", id: "fast" });

    resolveFirst?.();
    await slow;

    // The stale "node" response must not clobber the newer "org" selection.
    expect(useStore.getState().panels.inspector.data).toEqual({ kind: "org", id: "fast" });
  });
});
