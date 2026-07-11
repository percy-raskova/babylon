/**
 * Contract tests for the map slice (spec-110 B3, updated spec-113 Lane C) —
 * Lens/framing/viewport controls, and the selection-change -> InspectionStack
 * fan-out (`inspect.clear()+push()`, replacing the deleted
 * `panels.inspector.fetchForSelection`).
 */

import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";
import { DEFAULT_LENS } from "@/lib/lens";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("map slice — view controls", () => {
  it("defaults to lib/lens's DEFAULT_LENS, county framing, no selection, no faction filter", () => {
    // spec-113 Lane C (on Lane B's behalf, DESIGN_BIBLE.md §9.2/Carto
    // addendum): real county cartography is now the default visible map,
    // so "county" replaces "hex" as the default framing. The lens default
    // itself is Lane B's `lib/lens.ts::DEFAULT_LENS` (DESIGN_BIBLE.md §9.1
    // moved it to Imperial Rent Φ) — asserted against that export rather
    // than a hardcoded literal so this test can't drift from Lane B's file.
    const { map } = useStore.getState();
    expect(map.lens).toEqual(DEFAULT_LENS);
    expect(map.framing).toBe("county");
    expect(map.viewportBbox).toBeNull();
    expect(map.selection).toBeNull();
    expect(map.factionFilter).toBeNull();
  });

  it("setLens/setFraming/setViewportBbox update independently", () => {
    useStore.getState().map.setLens({ kind: "heat" });
    useStore.getState().map.setFraming("hex");
    useStore.getState().map.setViewportBbox([-84, 42, -83, 43]);

    const { map } = useStore.getState();
    expect(map.lens).toEqual({ kind: "heat" });
    expect(map.framing).toBe("hex");
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
    useStore.getState().map.setFraming("hex");
    await new Promise((r) => setTimeout(r, 0));

    expect(useStore.getState().map.framing).toBe("hex");
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

    useStore.getState().map.setFraming("hex");
    await new Promise((r) => setTimeout(r, 0));

    expect(useStore.getState().map.framing).toBe("hex");
    expect(requestLog.filter((r) => r === "GET map")).toHaveLength(1);
    expect(capturedUrl).toContain("zoom=hex");
  });
});

describe("map slice — selection fans out into the InspectionStack", () => {
  it("pushes a frame that carries a loud 'No active game' error when no active game is set", async () => {
    useStore.getState().map.setSelection({ kind: "hex", id: "h1" });
    await new Promise((r) => setTimeout(r, 0));

    expect(useStore.getState().map.selection).toEqual({ kind: "hex", id: "h1" });
    expect(useStore.getState().inspect.stack).toHaveLength(1);
    expect(useStore.getState().inspect.stack[0]?.error).toBe("No active game");
    expect(requestLog.filter((r) => r.startsWith("GET inspector"))).toHaveLength(0);
  });

  it("resolves an InspectionStack frame for the selection kind/id once a game is active", async () => {
    useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);

    useStore.getState().map.setSelection({ kind: "org", id: "org-1" });
    await new Promise((r) => setTimeout(r, 0));

    expect(requestLog.filter((r) => r === "GET inspector:org")).toHaveLength(1);
    const [frame] = useStore.getState().inspect.stack;
    expect(frame?.ref).toEqual({ kind: "org", id: "org-1" });
    expect(frame?.data).not.toBeNull();
    expect(frame?.error).toBeNull();
  });

  it("clearing the selection (null) clears the InspectionStack without a fetch", async () => {
    useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);
    useStore.getState().map.setSelection({ kind: "hex", id: "h1" });
    await new Promise((r) => setTimeout(r, 0));
    expect(useStore.getState().inspect.stack).toHaveLength(1);

    useStore.getState().map.setSelection(null);

    expect(useStore.getState().map.selection).toBeNull();
    expect(useStore.getState().inspect.stack).toHaveLength(0);
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

    useStore.getState().map.setSelection({ kind: "node", id: "n1" });
    useStore.getState().map.setSelection({ kind: "org", id: "fast" });
    await new Promise((r) => setTimeout(r, 0));
    expect(useStore.getState().inspect.stack).toHaveLength(1);
    expect(useStore.getState().inspect.stack[0]?.ref).toEqual({ kind: "org", id: "fast" });

    resolveFirst?.();
    await new Promise((r) => setTimeout(r, 0));

    // The stale "node" response must not clobber the newer "org" selection.
    expect(useStore.getState().inspect.stack).toHaveLength(1);
    expect(useStore.getState().inspect.stack[0]?.ref).toEqual({ kind: "org", id: "fast" });
    expect(useStore.getState().inspect.stack[0]?.data?.ref).toEqual({ kind: "org", id: "fast" });
    expect(useStore.getState().inspect.stack[0]?.data?.title).toBe("fast");
  });
});
