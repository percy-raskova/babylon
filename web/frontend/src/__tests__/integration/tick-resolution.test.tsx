/**
 * Integration test: tick resolution flow.
 *
 * Tests resolve tick → results display → state refresh cycle.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GameShell } from "@/components/layout/GameShell";
import { useGameStore } from "@/stores/gameStore";
import { makeSnapshot, makeActionResult } from "@/test/fixtures";

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
      resolveTick: vi.fn().mockResolvedValue([
        makeActionResult({
          org_id: "org-workers-union",
          action_type: "educate",
          success: true,
        }),
      ]),
      refresh: vi.fn().mockResolvedValue(undefined),
    };
  },
}));

describe("tick resolution flow", () => {
  it("clicking Resolve Tick shows results", async () => {
    const user = userEvent.setup();
    const snapshot = makeSnapshot({ tick: 3 });
    useGameStore.setState({ snapshot, loading: false });

    render(
      <GameShell gameId="game-001" username="testplayer" onBack={vi.fn()} onLogout={vi.fn()} />,
    );

    // Click resolve — TopBar and ActionComposer both have "Resolve Tick"
    const resolveButtons = screen.getAllByText("Resolve Tick");
    await user.click(resolveButtons[0]!);

    // Results should appear - TickResults shows org_id and action_type
    await waitFor(() => {
      expect(screen.getByText("org-workers-union")).toBeInTheDocument();
    });
    expect(screen.getByText("SUCCESS")).toBeInTheDocument();
  });

  it("tick counter reflects snapshot tick value", () => {
    useGameStore.setState({ snapshot: makeSnapshot({ tick: 7 }), loading: false });

    render(
      <GameShell gameId="game-001" username="testplayer" onBack={vi.fn()} onLogout={vi.fn()} />,
    );

    // The tick counter has "7" in the bold text-2xl element
    const tickElements = screen.getAllByText("7");
    expect(tickElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Tick")).toBeInTheDocument();
  });

  it("error state shows banner in game shell", () => {
    useGameStore.setState({
      snapshot: makeSnapshot(),
      error: "Network timeout",
      loading: false,
    });

    render(
      <GameShell gameId="game-001" username="testplayer" onBack={vi.fn()} onLogout={vi.fn()} />,
    );

    expect(screen.getByText("Network timeout")).toBeInTheDocument();
  });
});
