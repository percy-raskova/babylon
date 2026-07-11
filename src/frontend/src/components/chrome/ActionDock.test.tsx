/**
 * ActionDock tests — bottom-center dock hosting `ActionComposer`
 * (architecture §1.2's `RightDock` disperse row, Actions tab).
 *
 * Keeps `region-dock` (real-loop.spec.ts, unowned by this lane, still
 * references it — architecture §6's testid-contract risk) as the
 * successor testid: RightDock's default tab was Actions, and this is its
 * direct successor container.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActionDock } from "./ActionDock";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("ActionDock", () => {
  it("renders the region-dock landmark and hosts ActionComposer", () => {
    render(<ActionDock gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("region-dock")).toBeInTheDocument();
    expect(screen.getByTestId("action-composer")).toBeInTheDocument();
  });
});
