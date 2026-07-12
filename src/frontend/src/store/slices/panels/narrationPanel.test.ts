/**
 * Red-first tests for `createNarrationPanel` (Program 16 Lane N).
 *
 * This slice creator is deliberately NOT registered in `panels/index.ts` /
 * `store/index.ts` yet (owner directive: typed slots + mocks now, real
 * store wiring lands with the orchestrator later) — tests exercise the
 * factory directly, the same harness style `panelFactory.test.ts` uses.
 */

import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { createNarrationPanel, type NarrationPanel } from "./narrationPanel";
import type { NarrationBeat } from "@/types/narration";

function beat(overrides: Partial<NarrationBeat>): NarrationBeat {
  return {
    id: "beat-1",
    tick: 104,
    scope: "event",
    subjectRef: "evt-1",
    headline: "Federal agents raided the WCLF hall, tick 104.",
    body: "Federal agents breached the WCLF hall on Schaefer before dawn.",
    register: "wire",
    ...overrides,
  };
}

/** Minimal store double: only the one panel exists, wired the same way
 * `panelFactory`-based panels are wired into `panels/index.ts`. */
function makeHarness() {
  let panel: NarrationPanel;
  const updateSelf = (updater: (p: NarrationPanel) => NarrationPanel): void => {
    panel = updater(panel);
  };
  const getSelf = (): NarrationPanel => panel;

  panel = createNarrationPanel(updateSelf, getSelf);

  return { get: () => panel };
}

describe("createNarrationPanel", () => {
  it("starts idle/unmounted, offline, with no beats", () => {
    const { get } = makeHarness();
    expect(get()).toMatchObject({
      status: "offline",
      beats: [],
      loading: false,
      error: null,
      mounted: false,
    });
  });

  it("setMounted flips the mounted flag without touching beats/status", () => {
    const { get } = makeHarness();
    get().setMounted(true);
    expect(get().mounted).toBe(true);
    expect(get().status).toBe("offline");
  });

  it("fetch populates beats and flips status to ready on success", async () => {
    server.use(
      http.get("/api/games/g1/narration/", () =>
        HttpResponse.json({
          status: "ok",
          data: { status: "ready", beats: [beat({ id: "b1" })] },
        }),
      ),
    );
    const { get } = makeHarness();

    const promise = get().fetch("g1");
    expect(get().loading).toBe(true);
    await promise;

    expect(get().loading).toBe(false);
    expect(get().error).toBeNull();
    expect(get().status).toBe("ready");
    expect(get().beats).toEqual([beat({ id: "b1" })]);
  });

  it("404 (endpoint not implemented) degrades to offline, never surfaces an error string", async () => {
    server.use(
      http.get("/api/games/g1/narration/", () =>
        HttpResponse.json({ status: "error", message: "Not Found" }, { status: 404 }),
      ),
    );
    const { get } = makeHarness();

    await get().fetch("g1");

    expect(get().status).toBe("offline");
    expect(get().error).toBeNull();
    expect(get().beats).toEqual([]);
  });

  it("pending status carries no beats but is distinct from offline", async () => {
    server.use(
      http.get("/api/games/g1/narration/", () =>
        HttpResponse.json({ status: "ok", data: { status: "pending", beats: [] } }),
      ),
    );
    const { get } = makeHarness();

    await get().fetch("g1");

    expect(get().status).toBe("pending");
    expect(get().beats).toEqual([]);
  });

  it("a second fetch requests since_tick from the highest tick already held, and merges new beats in", async () => {
    let secondUrl = "";
    let callCount = 0;
    server.use(
      http.get("/api/games/g1/narration/", ({ request }) => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json({
            status: "ok",
            data: { status: "ready", beats: [beat({ id: "b1", tick: 104 })] },
          });
        }
        secondUrl = request.url;
        return HttpResponse.json({
          status: "ok",
          data: { status: "ready", beats: [beat({ id: "b2", tick: 105 })] },
        });
      }),
    );
    const { get } = makeHarness();

    await get().fetch("g1");
    await get().fetch("g1");

    expect(secondUrl).toContain("since_tick=104");
    expect(get().beats.map((b) => b.id)).toEqual(["b1", "b2"]);
  });

  it("refetching the same beat id does not duplicate it", async () => {
    server.use(
      http.get("/api/games/g1/narration/", () =>
        HttpResponse.json({
          status: "ok",
          data: { status: "ready", beats: [beat({ id: "b1", tick: 104 })] },
        }),
      ),
    );
    const { get } = makeHarness();

    await get().fetch("g1");
    await get().fetch("g1");

    expect(get().beats).toHaveLength(1);
  });

  it("preserves method identity across state updates (fetch/setMounted stay stable references)", async () => {
    server.use(
      http.get("/api/games/g1/narration/", () =>
        HttpResponse.json({ status: "ok", data: { status: "ready", beats: [] } }),
      ),
    );
    const { get } = makeHarness();
    const fetchRef = get().fetch;
    const setMountedRef = get().setMounted;

    await get().fetch("g1");

    expect(get().fetch).toBe(fetchRef);
    expect(get().setMounted).toBe(setMountedRef);
  });
});
