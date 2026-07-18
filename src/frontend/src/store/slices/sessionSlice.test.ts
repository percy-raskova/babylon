/**
 * Contract tests for the session slice — auth + lobby (spec-110 B3).
 *
 * Mirrors the real Django endpoints (`/accounts/whoami/`, `/accounts/login/`,
 * `/accounts/logout/`, `/api/games/`, `/api/scenarios/`) via the MSW
 * handlers in `src/test/handlers.ts` — no invented endpoints.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { useStore } from "@/store";
import { makeGameSummary } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("session slice — auth", () => {
  it("starts checking auth, then resolves to unauthenticated when whoami says so", async () => {
    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.json({ status: "ok", data: { is_authenticated: false } }),
      ),
    );

    expect(useStore.getState().session.authChecking).toBe(true);
    await useStore.getState().session.checkAuth();

    expect(useStore.getState().session.authChecking).toBe(false);
    expect(useStore.getState().session.auth).toBeNull();
  });

  it("checkAuth populates auth when whoami confirms authentication", async () => {
    await useStore.getState().session.checkAuth();

    const { auth, authChecking } = useStore.getState().session;
    expect(authChecking).toBe(false);
    expect(auth).toEqual({ is_authenticated: true, id: 1, username: "testuser" });
  });

  it("login success sets auth and returns true", async () => {
    const ok = await useStore.getState().session.login("testuser", "pw");

    expect(ok).toBe(true);
    expect(useStore.getState().session.auth).toEqual({
      is_authenticated: true,
      username: "testuser",
    });
  });

  it("login failure sets the error message and returns false, leaving auth null", async () => {
    server.use(
      http.post("/accounts/login/", () =>
        HttpResponse.json({ status: "error", message: "Invalid credentials" }, { status: 400 }),
      ),
    );

    const ok = await useStore.getState().session.login("testuser", "wrong");

    expect(ok).toBe(false);
    expect(useStore.getState().session.auth).toBeNull();
    expect(useStore.getState().session.error).toBe("Invalid credentials");
  });

  it("logout clears auth and the games list", async () => {
    await useStore.getState().session.checkAuth();
    await useStore.getState().session.fetchGames();
    expect(useStore.getState().session.games.length).toBeGreaterThan(0);

    await useStore.getState().session.logout();

    expect(useStore.getState().session.auth).toBeNull();
    expect(useStore.getState().session.games).toEqual([]);
  });
});

describe("session slice — lobby", () => {
  it("fetchGames populates the games list", async () => {
    await useStore.getState().session.fetchGames();

    const { games, gamesLoading } = useStore.getState().session;
    expect(gamesLoading).toBe(false);
    expect(games).toHaveLength(1);
    expect(games[0]?.id).toBe(DEFAULT_GAME_ID);
  });

  it("fetchScenarios populates the scenario catalog", async () => {
    await useStore.getState().session.fetchScenarios();

    expect(useStore.getState().session.scenarios).toEqual([
      expect.objectContaining({ key: "wayne_county" }),
    ]);
  });

  it("createGame returns the new session id and refreshes the games list", async () => {
    const id = await useStore.getState().session.createGame({ scenario: "wayne_county" });

    expect(id).toBe(DEFAULT_GAME_ID);
    expect(useStore.getState().session.games.length).toBeGreaterThan(0);
  });

  it("createGame returns null and records the error on failure", async () => {
    server.use(
      http.post("/api/games/", () =>
        HttpResponse.json({ status: "error", message: "Invalid scenario" }, { status: 400 }),
      ),
    );

    const id = await useStore.getState().session.createGame({ scenario: "bogus" });

    expect(id).toBeNull();
    expect(useStore.getState().session.error).toBe("Invalid scenario");
  });

  it("setActiveGame updates activeGameId", () => {
    useStore.getState().session.setActiveGame("g-42");
    expect(useStore.getState().session.activeGameId).toBe("g-42");
    useStore.getState().session.setActiveGame(null);
    expect(useStore.getState().session.activeGameId).toBeNull();
  });
});

describe("session slice — delete/archive (spec-116 FR-116-3)", () => {
  it("deleteGame issues DELETE /api/games/:id/ and refreshes the list", async () => {
    let deleted = false;
    server.use(
      http.delete("/api/games/:id/", () => {
        deleted = true;
        return HttpResponse.json({ status: "ok", data: { deleted: true } });
      }),
      http.get("/api/games/", () =>
        HttpResponse.json({ status: "ok", data: deleted ? [] : [makeGameSummary()] }),
      ),
    );

    const ok = await useStore.getState().session.deleteGame(DEFAULT_GAME_ID);

    expect(ok).toBe(true);
    expect(deleted).toBe(true);
    expect(useStore.getState().session.games).toEqual([]);
  });

  it("deleteGame failure records the error and returns false", async () => {
    server.use(
      http.delete("/api/games/:id/", () =>
        HttpResponse.json({ status: "error", message: "Game not found" }, { status: 404 }),
      ),
    );

    const ok = await useStore.getState().session.deleteGame(DEFAULT_GAME_ID);

    expect(ok).toBe(false);
    expect(useStore.getState().session.error).toBe("Game not found");
  });

  it("archiveGame POSTs /archive/ and refreshes the list", async () => {
    let archived = false;
    server.use(
      http.post("/api/games/:id/archive/", () => {
        archived = true;
        return HttpResponse.json({ status: "ok", data: { status: "abandoned" } });
      }),
      http.get("/api/games/", () =>
        HttpResponse.json({
          status: "ok",
          data: [makeGameSummary({ status: archived ? "abandoned" : "active" })],
        }),
      ),
    );

    const ok = await useStore.getState().session.archiveGame(DEFAULT_GAME_ID);

    expect(ok).toBe(true);
    expect(useStore.getState().session.games[0]?.status).toBe("abandoned");
  });

  it("archiveGame failure records the error and returns false", async () => {
    server.use(
      http.post("/api/games/:id/archive/", () =>
        HttpResponse.json(
          { status: "error", message: "Game is already archived" },
          { status: 400 },
        ),
      ),
    );

    const ok = await useStore.getState().session.archiveGame(DEFAULT_GAME_ID);

    expect(ok).toBe(false);
    expect(useStore.getState().session.error).toBe("Game is already archived");
  });
});
