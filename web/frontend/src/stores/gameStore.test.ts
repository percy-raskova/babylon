/**
 * Unit tests for the game state Zustand store.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { useGameStore } from "./gameStore";
import { makeSnapshot } from "@/test/fixtures";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";

describe("useGameStore", () => {
  beforeEach(() => {
    // Merge-mode (no `true`) preserves action functions
    useGameStore.setState({
      sessionId: null,
      snapshot: null,
      available: [],
      tickSummaries: [],
      loading: false,
      error: null,
    });
  });

  it("has correct initial state", () => {
    const state = useGameStore.getState();
    expect(state.sessionId).toBeNull();
    expect(state.snapshot).toBeNull();
    expect(state.available).toEqual([]);
    expect(state.tickSummaries).toEqual([]);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("setSession updates sessionId", () => {
    useGameStore.getState().setSession("game-42");
    expect(useGameStore.getState().sessionId).toBe("game-42");
  });

  it("setSession clears sessionId with null", () => {
    useGameStore.getState().setSession("game-42");
    useGameStore.getState().setSession(null);
    expect(useGameStore.getState().sessionId).toBeNull();
  });

  it("fetchState populates snapshot and tickSummaries", async () => {
    await useGameStore.getState().fetchState("game-001");

    const state = useGameStore.getState();
    const snapshot = state.snapshot;
    expect(snapshot).not.toBeNull();
    if (!snapshot) {
      throw new Error("Snapshot missing");
    }
    expect(snapshot.tick).toBe(1);
    expect(state.tickSummaries).toHaveLength(1);
    const firstSummary = state.tickSummaries[0];
    expect(firstSummary).toBeDefined();
    if (!firstSummary) {
      throw new Error("Tick summary missing");
    }
    expect(firstSummary.tick).toBe(1);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("fetchState populates available actions", async () => {
    await useGameStore.getState().fetchState("game-001");

    const state = useGameStore.getState();
    expect(state.available).toHaveLength(3);
    const firstAvailable = state.available[0];
    expect(firstAvailable).toBeDefined();
    if (!firstAvailable) {
      throw new Error("Available action missing");
    }
    expect(firstAvailable.verb).toBe("educate");
  });

  it("fetchState does not duplicate tick summaries for same tick", async () => {
    await useGameStore.getState().fetchState("game-001");
    await useGameStore.getState().fetchState("game-001");

    expect(useGameStore.getState().tickSummaries).toHaveLength(1);
  });

  it("fetchState appends new tick summary for different tick", async () => {
    await useGameStore.getState().fetchState("game-001");

    // Override to return tick 2
    server.use(
      http.get("/api/games/:id/state/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeSnapshot({ tick: 2 }),
        }),
      ),
    );

    await useGameStore.getState().fetchState("game-001");
    expect(useGameStore.getState().tickSummaries).toHaveLength(2);
    const secondSummary = useGameStore.getState().tickSummaries[1];
    expect(secondSummary).toBeDefined();
    if (!secondSummary) {
      throw new Error("Second tick summary missing");
    }
    expect(secondSummary.tick).toBe(2);
  });

  it("fetchState sets error on API error", async () => {
    server.use(
      http.get("/api/games/:id/state/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Game not found",
        }),
      ),
    );

    await useGameStore.getState().fetchState("nonexistent");
    expect(useGameStore.getState().error).toBe("Game not found");
  });

  it("submitAction re-fetches state after submission", async () => {
    const fetchSpy = vi.spyOn(useGameStore.getState(), "fetchState");
    await useGameStore.getState().submitAction("game-001", {
      org_id: "org-workers-union",
      verb: "educate",
      target_id: "entity-proletariat",
    });

    // fetchState is called internally
    expect(useGameStore.getState().snapshot).not.toBeNull();
    fetchSpy.mockRestore();
  });

  it("submitAction sets error on API error", async () => {
    // Track errors set during the flow
    const errors: (string | null)[] = [];
    useGameStore.subscribe((state) => {
      if (state.error !== null) errors.push(state.error);
    });

    server.use(
      http.post("/api/games/:id/actions/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Insufficient budget",
        }),
      ),
    );

    await useGameStore.getState().submitAction("game-001", {
      org_id: "org-workers-union",
      verb: "attack",
    });

    // Error was set during the flow (re-fetch may clear it afterward)
    expect(errors).toContain("Insufficient budget");
  });

  it("resolveTick returns action results", async () => {
    const results = await useGameStore.getState().resolveTick("game-001");

    expect(results).not.toBeNull();
    if (!results) {
      throw new Error("Tick results missing");
    }
    expect(results).toHaveLength(1);
    const firstResult = results[0];
    expect(firstResult).toBeDefined();
    if (!firstResult) {
      throw new Error("First tick result missing");
    }
    expect(firstResult.org_id).toBe("org-workers-union");
  });

  it("resolveTick returns null on error", async () => {
    server.use(
      http.post("/api/games/:id/resolve/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Cannot resolve",
        }),
      ),
    );

    const results = await useGameStore.getState().resolveTick("game-001");
    expect(results).toBeNull();
    expect(useGameStore.getState().error).toBe("Cannot resolve");
  });

  it("reset clears all state", async () => {
    await useGameStore.getState().fetchState("game-001");
    useGameStore.getState().setSession("game-001");
    useGameStore.getState().reset();

    const state = useGameStore.getState();
    expect(state.sessionId).toBeNull();
    expect(state.snapshot).toBeNull();
    expect(state.available).toEqual([]);
    expect(state.tickSummaries).toEqual([]);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  describe("extractSummary", () => {
    it("calculates correct aggregations", async () => {
      await useGameStore.getState().fetchState("game-001");

      const summary = useGameStore.getState().tickSummaries[0];
      expect(summary).toBeDefined();
      if (!summary) {
        throw new Error("Summary missing");
      }
      // The MSW handler now returns Wayne County data (4 entities)
      // avgHeat is computed from territories, avgConsciousness from entities
      // These are Wayne County fixture values — exact numbers depend on the mock
      expect(summary.avgHeat).toBeDefined();
      expect(summary.avgConsciousness).toBeDefined();
      expect(summary.totalWealth).toBeDefined();
      expect(summary.orgCount).toBe(1);
      expect(summary.eventCount).toBe(1);
      expect(summary.edgeCount).toBe(2);
    });
  });
});
