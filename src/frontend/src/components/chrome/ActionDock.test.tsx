/**
 * ActionDock tests — bottom-center dock: a compact ≤3-verb bar +
 * `ActionComposer` FloatingPanel (architecture §1.2's `RightDock` disperse
 * row, Actions tab; Design Bible §5.1 Shneiderman progressive disclosure).
 *
 * Keeps `region-dock` (real-loop.spec.ts, unowned by this lane, still
 * references it — architecture §6's testid-contract risk) as the
 * successor testid: RightDock's default tab was Actions, and this is its
 * direct successor container.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ActionDock } from "./ActionDock";
import { useStore } from "@/store";
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

  it("shows at most 3 primary verbs plus a labeled More button", () => {
    render(<ActionDock gameId={DEFAULT_GAME_ID} />);
    const bar = screen.getByTestId("action-dock-bar");
    const primaryButtons = bar.querySelectorAll('[data-testid^="action-dock-verb-"]');
    expect(primaryButtons.length).toBeLessThanOrEqual(3);
    expect(screen.getByTestId("action-dock-more")).toHaveTextContent(/more/i);
  });

  it("never surfaces an engine-unwired verb (investigate/move/negotiate) as primary", () => {
    render(<ActionDock gameId={DEFAULT_GAME_ID} />);
    expect(screen.queryByTestId("action-dock-verb-investigate")).not.toBeInTheDocument();
    expect(screen.queryByTestId("action-dock-verb-move")).not.toBeInTheDocument();
    expect(screen.queryByTestId("action-dock-verb-negotiate")).not.toBeInTheDocument();
  });

  it("opens the composer from a collapsed state when a primary verb is clicked", async () => {
    useStore.setState((s) => ({
      ui: { ...s.ui, chrome: { ...s.ui.chrome, composerOpen: false } },
    }));
    render(<ActionDock gameId={DEFAULT_GAME_ID} />);
    expect(useStore.getState().ui.chrome.composerOpen).toBe(false);

    const bar = screen.getByTestId("action-dock-bar");
    const firstVerb = bar.querySelector<HTMLButtonElement>('[data-testid^="action-dock-verb-"]');
    expect(firstVerb).not.toBeNull();
    await userEvent.click(firstVerb as HTMLButtonElement);

    expect(useStore.getState().ui.chrome.composerOpen).toBe(true);
  });

  it("opens the composer from the More button too", async () => {
    useStore.setState((s) => ({
      ui: { ...s.ui, chrome: { ...s.ui.chrome, composerOpen: false } },
    }));
    render(<ActionDock gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("action-dock-more"));
    expect(useStore.getState().ui.chrome.composerOpen).toBe(true);
  });
});
