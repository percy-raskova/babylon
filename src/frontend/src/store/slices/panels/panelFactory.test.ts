/**
 * Unit tests for the panel factory (spec-110 B3) — the shape every docked
 * panel shares (data/loading/error/mounted + fetch/setMounted).
 */

import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { createPanel, type Panel } from "./panelFactory";
import type { RootState } from "../../types";

interface FakePayload {
  value: number;
}

/** Minimal store double shape: only `panels.fake` exists — wired the same
 * way `panels/index.ts` wires a real panel, but without dragging in the
 * full `RootState` (this factory only ever reads its own panel's slot). */
interface FakeHarnessState {
  panels: { fake: Panel<FakePayload> };
}

/** Minimal store double: only `panels.fake` exists, wired the same way
 * `panels/index.ts` wires a real panel. */
function makeHarness(
  endpoint: (gameId: string) => string = (gameId) => `/api/games/${gameId}/fake/`,
) {
  let panel: Panel<FakePayload>;
  const state: FakeHarnessState = {
    get panels() {
      return { fake: panel };
    },
  };

  const get = (): RootState => state as unknown as RootState;
  const set = (fn: (s: FakeHarnessState) => FakeHarnessState): void => {
    panel = fn(state).panels.fake;
  };

  panel = createPanel<FakePayload>(
    endpoint,
    (updater) => set((s) => ({ panels: { fake: updater(s.panels.fake) } })),
    get,
  );

  return { get: () => panel };
}

describe("createPanel", () => {
  it("starts in the idle/unmounted state", () => {
    const { get } = makeHarness();
    expect(get()).toMatchObject({ data: null, loading: false, error: null, mounted: false });
  });

  it("setMounted flips the mounted flag without touching data", async () => {
    const { get } = makeHarness();
    get().setMounted(true);
    expect(get().mounted).toBe(true);
    get().setMounted(false);
    expect(get().mounted).toBe(false);
  });

  it("fetch populates data on success and clears loading", async () => {
    server.use(
      http.get("/api/games/g1/fake/", () =>
        HttpResponse.json({ status: "ok", data: { value: 42 } }),
      ),
    );
    const { get } = makeHarness();

    const promise = get().fetch("g1");
    expect(get().loading).toBe(true);
    await promise;

    expect(get().loading).toBe(false);
    expect(get().error).toBeNull();
    expect(get().data).toEqual({ value: 42 });
  });

  it("fetch surfaces the backend error message and leaves data untouched", async () => {
    server.use(
      http.get("/api/games/g1/fake/", () =>
        HttpResponse.json({ status: "error", message: "boom" }, { status: 500 }),
      ),
    );
    const { get } = makeHarness();

    await get().fetch("g1");

    expect(get().loading).toBe(false);
    expect(get().error).toBe("boom");
    expect(get().data).toBeNull();
  });

  it("preserves method identity across state updates (fetch/setMounted stay stable references)", async () => {
    server.use(
      http.get("/api/games/g1/fake/", () =>
        HttpResponse.json({ status: "ok", data: { value: 1 } }),
      ),
    );
    const { get } = makeHarness();
    const fetchRef = get().fetch;
    const setMountedRef = get().setMounted;

    await get().fetch("g1");

    expect(get().fetch).toBe(fetchRef);
    expect(get().setMounted).toBe(setMountedRef);
  });

  it("endpoint receives the gameId it was called with", async () => {
    const seen: string[] = [];
    server.use(
      http.get("/api/games/:id/fake/", ({ params }) => {
        seen.push(String(params.id));
        return HttpResponse.json({ status: "ok", data: { value: 1 } });
      }),
    );
    const { get } = makeHarness();

    await get().fetch("alpha");
    await get().fetch("beta");

    expect(seen).toEqual(["alpha", "beta"]);
  });
});

describe("createPanel — vi.fn spy sanity", () => {
  it("does not call the endpoint builder until fetch() is invoked", () => {
    const endpoint = vi.fn((gameId: string) => `/api/games/${gameId}/fake/`);
    makeHarness(endpoint);

    expect(endpoint).not.toHaveBeenCalled();
  });
});
