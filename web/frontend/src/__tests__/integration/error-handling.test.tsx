/**
 * Integration test: error handling across components.
 *
 * Tests API errors, network failures, and graceful degradation.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from "@/components/LoginPage";
import { GameList } from "@/components/GameList";
import { GameShell } from "@/components/layout/GameShell";
import { useGameStore } from "@/stores/gameStore";
import { makeSnapshot } from "@/test/fixtures";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";

// Mock useGameState to avoid polling
vi.mock("@/hooks/useGameState", () => ({
  useGameState: (_gameId: string) => {
    const snapshot = useGameStore.getState().snapshot;
    const loading = useGameStore.getState().loading;
    const error = useGameStore.getState().error;
    return {
      snapshot,
      available: [],
      loading,
      error,
      submitAction: vi.fn().mockResolvedValue(undefined),
      resolveTick: vi.fn().mockResolvedValue([]),
      refresh: vi.fn().mockResolvedValue(undefined),
    };
  },
}));

describe("error handling", () => {
  it("login error shows message on form", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/accounts/login/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Account locked",
        }),
      ),
    );

    render(<LoginPage onLogin={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("Username"), "locked");
    await user.type(screen.getByPlaceholderText("Password"), "pass");
    await user.click(screen.getByText("Log In"));

    await waitFor(() => {
      expect(screen.getByText("Account locked")).toBeInTheDocument();
    });
  });

  it("game list fetch error shows message", async () => {
    server.use(
      http.get("/api/games/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Database unavailable",
        }),
      ),
    );

    render(<GameList onSelectGame={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Database unavailable")).toBeInTheDocument();
    });
  });

  it("game create error shows message on game list", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })),
      http.post("/api/games/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Max games reached",
        }),
      ),
    );

    render(<GameList onSelectGame={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("+ New Game")).toBeInTheDocument();
    });
    await user.click(screen.getByText("+ New Game"));

    await waitFor(() => {
      expect(screen.getByText("Max games reached")).toBeInTheDocument();
    });
  });

  it("game shell shows error banner from store", () => {
    useGameStore.setState({
      snapshot: makeSnapshot(),
      error: "Connection lost",
    });

    render(<GameShell gameId="game-001" username="player" onBack={vi.fn()} onLogout={vi.fn()} />);

    expect(screen.getByText("Connection lost")).toBeInTheDocument();
  });
});
