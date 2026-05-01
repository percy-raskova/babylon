/**
 * Unit tests for gameStore — verifies playerOrgs, verbTargets,
 * and invalidation lifecycle using MSW handlers.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { useGameStore } from "@/stores/gameStore";

describe("gameStore", () => {
  beforeEach(() => {
    useGameStore.getState().reset();
  });

  describe("fetchPlayerOrgs", () => {
    it("populates playerOrgs and sets playerOrgsLoaded on success", async () => {
      const orgs = [
        { id: "org-1", name: "Workers Union" },
        { id: "org-2", name: "Peoples Front" },
      ];

      server.use(
        http.get("/api/games/:id/organizations/", () =>
          HttpResponse.json({
            status: "ok",
            data: { organizations: orgs },
          }),
        ),
      );

      await useGameStore.getState().fetchPlayerOrgs("game-001");

      const state = useGameStore.getState();
      expect(state.playerOrgs).toEqual(orgs);
      expect(state.playerOrgsLoaded).toBe(true);
    });

    it("sets error on failure", async () => {
      server.use(
        http.get("/api/games/:id/organizations/", () =>
          HttpResponse.json({ status: "error", data: null, message: "Not found" }, { status: 404 }),
        ),
      );

      await useGameStore.getState().fetchPlayerOrgs("game-001");

      const state = useGameStore.getState();
      expect(state.playerOrgs).toEqual([]);
      expect(state.playerOrgsLoaded).toBe(false);
      expect(state.error).toBe("Not found");
    });
  });

  describe("fetchVerbTargets", () => {
    it("caches target data by composite key", async () => {
      const targets = { targets: [{ id: "t-1", name: "Downtown" }] };

      server.use(
        http.get("/api/games/:id/actions/:verb/targets/", () =>
          HttpResponse.json({ status: "ok", data: targets }),
        ),
      );

      await useGameStore.getState().fetchVerbTargets("game-001", "educate", "org-1");

      const state = useGameStore.getState();
      expect(state.verbTargets["educate:org-1"]).toEqual(targets);
    });

    it("preserves existing cache entries when adding new ones", async () => {
      // Seed an existing entry
      useGameStore.setState({
        verbTargets: { "aid:org-1": { targets: [] } },
      });

      server.use(
        http.get("/api/games/:id/actions/:verb/targets/", () =>
          HttpResponse.json({
            status: "ok",
            data: { targets: [{ id: "t-2" }] },
          }),
        ),
      );

      await useGameStore.getState().fetchVerbTargets("game-001", "attack", "org-2");

      const state = useGameStore.getState();
      expect(state.verbTargets["aid:org-1"]).toBeDefined();
      expect(state.verbTargets["attack:org-2"]).toBeDefined();
    });
  });

  describe("invalidateVerbTargets", () => {
    it("clears all cached verb targets", () => {
      useGameStore.setState({
        verbTargets: {
          "educate:org-1": { targets: [] },
          "aid:org-2": { targets: [] },
        },
      });

      useGameStore.getState().invalidateVerbTargets();

      expect(useGameStore.getState().verbTargets).toEqual({});
    });
  });

  describe("reset", () => {
    it("clears playerOrgs, playerOrgsLoaded, and verbTargets", () => {
      useGameStore.setState({
        playerOrgs: [{ id: "org-1" }] as never,
        playerOrgsLoaded: true,
        verbTargets: { "educate:org-1": {} },
        sessionId: "s-1",
      });

      useGameStore.getState().reset();

      const state = useGameStore.getState();
      expect(state.playerOrgs).toEqual([]);
      expect(state.playerOrgsLoaded).toBe(false);
      expect(state.verbTargets).toEqual({});
      expect(state.sessionId).toBeNull();
    });
  });
});
