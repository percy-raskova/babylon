/**
 * TopBar tests — ports StatusBar.test.tsx's real-/summary/-data assertions
 * (architecture §1.2's "StatusBar → TopBar, migrate" row) onto the new
 * chrome component. Keeps `region-statusbar`/`tick-value` testids.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TopBar } from "./TopBar";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import { makeSnapshot, makeGameSummaryPayload } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("TopBar", () => {
  it("renders as the region-statusbar landmark", () => {
    render(<TopBar gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("region-statusbar")).toBeInTheDocument();
  });

  it("fetches and renders real /summary/ fields", async () => {
    render(<TopBar gameId={DEFAULT_GAME_ID} />);

    await waitFor(() => expect(useStore.getState().panels.summary.data).not.toBeNull());

    expect(screen.getByTestId("stat-profit")).toHaveTextContent("no data"); // fixture sets profit_rate: null
    expect(screen.getByTestId("stat-rent φ")).toHaveTextContent("12.50");
    expect(screen.getByTestId("stat-pop")).toHaveTextContent("42,000");
  });

  it("shows the tick from world.snapshot, not the summary panel", async () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: makeSnapshot({ tick: 7 }), lastTick: 7 },
    }));
    render(<TopBar gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("tick-value")).toHaveTextContent("7");
  });

  it("shows 'no data' for tick when no snapshot has loaded yet", () => {
    render(<TopBar gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("tick-value")).toHaveTextContent("no data");
  });

  it("renders alert-count badges only when there are critical/warning events", async () => {
    server.use(
      http.get("/api/games/:id/summary/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeGameSummaryPayload({
            event_counts: { critical: 2, warning: 1, informational: 5 },
          }),
        }),
      ),
    );
    render(<TopBar gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("alert-counts")).toBeInTheDocument());
    expect(screen.getByTitle("2 critical events")).toHaveTextContent("2");
    expect(screen.getByTitle("1 warning events")).toHaveTextContent("1");
  });

  it("mounts and unmounts the summary panel", async () => {
    const { unmount } = render(<TopBar gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.summary.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.summary.mounted).toBe(false);
  });

  it("opens each takeover from its TopBar button (spec-110 B5)", async () => {
    render(<TopBar gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByTestId("open-wire"));
    expect(useStore.getState().ui.takeover.active).toBe("wire");

    await userEvent.click(screen.getByTestId("open-dialectic"));
    expect(useStore.getState().ui.takeover.active).toBe("dialectic");

    await userEvent.click(screen.getByTestId("open-chronicle"));
    expect(useStore.getState().ui.takeover.active).toBe("chronicle");
  });

  it("hosts SpeedControls (time-status testid survives the TimeControls → SpeedControls migration)", () => {
    render(<TopBar gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("time-status")).toBeInTheDocument();
  });
});
