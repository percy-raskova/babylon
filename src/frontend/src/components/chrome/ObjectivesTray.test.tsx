/**
 * ObjectivesTray tests — hosts `ObjectivesTracker` (architecture §1.2's
 * `RightDock` disperse row, Objectives tab).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ObjectivesTray } from "./ObjectivesTray";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot } from "@/test/fixtures";
import type { EndgameProgress } from "@/types/game";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("ObjectivesTray", () => {
  it("renders its testid and hosts ObjectivesTracker's real data", async () => {
    render(<ObjectivesTray gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("objectives-tray")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Revolutionary Victory")).toBeInTheDocument());
  });

  it("badges the header with the active objective count", async () => {
    render(<ObjectivesTray gameId={DEFAULT_GAME_ID} />);
    // Default mock fixture (makeObjectivesTracker) ships one active objective.
    await waitFor(() => expect(screen.getByText("Objectives (1)")).toBeInTheDocument());
  });
});

describe("ObjectivesTray — accept-outcome mercy affordance (spec-116 FR-116-5)", () => {
  const LOCKED_PROGRESS: EndgameProgress = {
    axes: {
      revolutionary_victory: 0,
      ecological_collapse: 0,
      fascist_consolidation: 1,
      red_ogv: 0,
      fragmented_collapse: 0,
    },
    pattern: "fascist_consolidation",
    since_tick: 1,
    horizon_tick: 5200,
    locked: true,
  };

  it("does not render the accept-outcome button when no pattern is locked", () => {
    render(<ObjectivesTray gameId={DEFAULT_GAME_ID} />);
    expect(screen.queryByTestId("accept-outcome")).not.toBeInTheDocument();
  });

  it("renders the accept-outcome button once endgame_progress.locked is true", () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({ session_id: DEFAULT_GAME_ID, endgame_progress: LOCKED_PROGRESS }),
      },
    }));

    render(<ObjectivesTray gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("accept-outcome")).toBeInTheDocument();
  });

  it("calls world.acceptOutcome with the game id when clicked", async () => {
    const acceptOutcome = vi.fn().mockResolvedValue(undefined);
    useStore.setState((s) => ({
      world: {
        ...s.world,
        acceptOutcome,
        snapshot: makeSnapshot({ session_id: DEFAULT_GAME_ID, endgame_progress: LOCKED_PROGRESS }),
      },
    }));

    render(<ObjectivesTray gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("accept-outcome"));

    expect(acceptOutcome).toHaveBeenCalledWith(DEFAULT_GAME_ID);
  });
});
