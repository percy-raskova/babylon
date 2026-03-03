/**
 * Unit tests for the GameList component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GameList } from "./GameList";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import { makeGameSummary } from "@/test/fixtures";

describe("GameList", () => {
  it("shows loading state initially", () => {
    // Use a delayed handler so loading state persists
    server.use(
      http.get("/api/games/", async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({ status: "ok", data: [] });
      }),
    );
    render(<GameList onSelectGame={vi.fn()} />);
    expect(screen.getByText("Loading games...")).toBeInTheDocument();
  });

  it("shows empty state when no games", async () => {
    server.use(http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })));
    render(<GameList onSelectGame={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("No games yet. Create one to begin.")).toBeInTheDocument();
    });
  });

  it("lists games from API", async () => {
    const games = [
      makeGameSummary({ id: "game-001", scenario: "Detroit Scenario", current_tick: 5 }),
      makeGameSummary({ id: "game-002", scenario: "National Crisis", current_tick: 12 }),
    ];
    server.use(http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: games })));
    render(<GameList onSelectGame={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Detroit Scenario")).toBeInTheDocument();
    });
    expect(screen.getByText("National Crisis")).toBeInTheDocument();
    expect(screen.getByText("Tick 5")).toBeInTheDocument();
    expect(screen.getByText("Tick 12")).toBeInTheDocument();
  });

  it("calls onSelectGame when clicking a game", async () => {
    const user = userEvent.setup();
    const onSelectGame = vi.fn();
    server.use(
      http.get("/api/games/", () =>
        HttpResponse.json({
          status: "ok",
          data: [makeGameSummary({ id: "game-abc", scenario: "Test" })],
        }),
      ),
    );
    render(<GameList onSelectGame={onSelectGame} />);

    await waitFor(() => {
      expect(screen.getByText("Test")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Test"));
    expect(onSelectGame).toHaveBeenCalledWith("game-abc");
  });

  it("shows create button and creating state", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })),
      http.post("/api/games/", async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json({
          status: "ok",
          data: { session_id: "new-game-id" },
        });
      }),
    );
    const onSelectGame = vi.fn();
    render(<GameList onSelectGame={onSelectGame} />);

    await waitFor(() => {
      expect(screen.getByText("+ New Game")).toBeInTheDocument();
    });

    await user.click(screen.getByText("+ New Game"));
    expect(screen.getByText("Creating...")).toBeInTheDocument();

    await waitFor(() => {
      expect(onSelectGame).toHaveBeenCalledWith("new-game-id");
    });
  });

  it("shows error on failed fetch", async () => {
    server.use(
      http.get("/api/games/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Server unavailable",
        }),
      ),
    );
    render(<GameList onSelectGame={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Server unavailable")).toBeInTheDocument();
    });
  });

  it("shows error and exits loading on non-JSON fetch failure", async () => {
    server.use(
      http.get("/api/games/", () =>
        HttpResponse.text("<html>bad gateway</html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    render(<GameList onSelectGame={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("HTTP 502")).toBeInTheDocument();
    });
    expect(screen.queryByText("Loading games...")).not.toBeInTheDocument();
  });
});
