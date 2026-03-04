/**
 * Unit tests for the GameShell component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { GameShell } from "./GameShell";
import { useGameStore } from "@/stores/gameStore";
import { makeSnapshot } from "@/test/fixtures";

// Mock useGameState hook to avoid polling
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

/** Render GameShell inside a MemoryRouter with route param. */
function renderShell(props?: Partial<{ username: string }>) {
  return render(
    <MemoryRouter initialEntries={["/games/game-001"]}>
      <Routes>
        <Route
          path="/games/:id"
          element={
            <GameShell
              username={props?.username ?? "testplayer"}
              onBack={vi.fn()}
              onLogout={vi.fn()}
            />
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("GameShell", () => {
  it("shows loading state when no snapshot", () => {
    useGameStore.setState({ loading: true, snapshot: null });
    renderShell();
    expect(screen.getByText("Loading game state...")).toBeInTheDocument();
  });

  it("shows no state available when not loading and no snapshot", () => {
    useGameStore.setState({ loading: false, snapshot: null });
    renderShell();
    expect(screen.getByText("No state available")).toBeInTheDocument();
  });

  it("renders map and panels when snapshot is available", () => {
    useGameStore.setState({ snapshot: makeSnapshot(), loading: false });
    renderShell();

    // TopBar elements
    expect(screen.getByText("testplayer")).toBeInTheDocument();
    // Actions section
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });

  it("shows error message", () => {
    useGameStore.setState({ snapshot: makeSnapshot(), error: "Something broke" });
    renderShell();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("renders TopBar with tick counter", () => {
    useGameStore.setState({ snapshot: makeSnapshot() });
    renderShell();
    expect(screen.getByText("Tick")).toBeInTheDocument();
  });
});
