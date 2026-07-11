/**
 * ObjectivesTray tests — hosts `ObjectivesTracker` (architecture §1.2's
 * `RightDock` disperse row, Objectives tab).
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ObjectivesTray } from "./ObjectivesTray";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

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
});
