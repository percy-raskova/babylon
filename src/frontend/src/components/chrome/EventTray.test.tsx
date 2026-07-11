/**
 * EventTray tests — persistent right rail hosting `EventsFeed`
 * (architecture §1.2's `BottomStrip` disperse row; §4.2).
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventTray } from "./EventTray";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("EventTray", () => {
  it("renders its testid and hosts EventsFeed", () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: { ...s.world.snapshot, events: [] } as never },
    }));
    render(<EventTray gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("event-tray")).toBeInTheDocument();
    expect(screen.getByTestId("events-feed")).toBeInTheDocument();
  });

  it("collapses via ui.chrome.eventTrayOpen, keeping EventsFeed mounted but hidden", async () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: { ...s.world.snapshot, events: [] } as never },
    }));
    render(<EventTray gameId={DEFAULT_GAME_ID} />);
    expect(useStore.getState().ui.chrome.eventTrayOpen).toBe(true);

    await userEvent.click(screen.getByRole("button", { name: /[▾▸]/ }));
    expect(useStore.getState().ui.chrome.eventTrayOpen).toBe(false);
    expect(screen.getByTestId("events-feed")).toBeInTheDocument();
  });
});
