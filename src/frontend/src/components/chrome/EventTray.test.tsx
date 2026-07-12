/**
 * EventTray tests — persistent right rail hosting `EventsFeed`
 * (architecture §1.2's `BottomStrip` disperse row; §4.2), plus badge
 * counts, per-category mute toggles, and the recoverable dismissed tray.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventTray } from "./EventTray";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeEvent } from "@/test/fixtures";

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

  it("shows badge counts mirroring panels.summary.data.event_counts", () => {
    useStore.setState((s) => ({
      panels: {
        ...s.panels,
        summary: {
          ...s.panels.summary,
          data: {
            tick: 1,
            imperial_rent: null,
            avg_consciousness: null,
            population_total: null,
            exploitation_rate: null,
            profit_rate: null,
            org_count: 0,
            class_count: 0,
            event_counts: { critical: 2, warning: 1, informational: 0 },
          },
        },
      },
    }));

    render(<EventTray gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("event-tray-count-critical")).toHaveTextContent("2");
    expect(screen.getByTestId("event-tray-count-warning")).toHaveTextContent("1");
    expect(screen.queryByTestId("event-tray-count-informational")).not.toBeInTheDocument();
  });

  it("toggling a mute-toggle button mutes/unmutes that category", async () => {
    render(<EventTray gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByTestId("mute-toggle-struggle"));
    expect(useStore.getState().events.mutedCategories).toEqual(["struggle"]);
    expect(screen.getByTestId("mute-toggle-struggle")).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(screen.getByTestId("mute-toggle-struggle"));
    expect(useStore.getState().events.mutedCategories).toEqual([]);
  });

  it("lists dismissed toasts in the recoverable tray and restores them", async () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
    const id = useStore.getState().events.toasts[0]!.id;
    useStore.getState().events.dismissToast(id);

    render(<EventTray gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("event-tray-dismissed")).toBeInTheDocument();
    expect(screen.getByTestId(`tray-restore-${id}`)).toBeInTheDocument();

    await userEvent.click(screen.getByTestId(`tray-restore-${id}`));

    expect(useStore.getState().events.tray).toHaveLength(0);
    expect(useStore.getState().events.toasts).toHaveLength(1);
  });

  it("omits the dismissed-tray section entirely when nothing has been dismissed", () => {
    render(<EventTray gameId={DEFAULT_GAME_ID} />);
    expect(screen.queryByTestId("event-tray-dismissed")).not.toBeInTheDocument();
  });
});
