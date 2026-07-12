/**
 * BottomDrawer tests — "Trends" drawer hosting `TimeseriesChart`
 * (architecture §1.2's `BottomStrip` disperse row), always mounted while
 * hidden so `panels.timeseries` stays fanned out.
 *
 * Keeps `region-bottomstrip` (architecture §6 testid-contract risk —
 * real-loop.spec.ts, owned by Lane G, still asserts it) as the successor
 * testid: `BottomStrip`'s layout diagram slot ("BottomDrawer toggle
 * Trends/Events") is its direct successor container.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BottomDrawer } from "./BottomDrawer";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("BottomDrawer", () => {
  it("renders the region-bottomstrip landmark and defaults to Trends (TimeseriesChart)", async () => {
    render(<BottomDrawer gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("region-bottomstrip")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("timeseries-chart")).toBeInTheDocument());
  });

  it("keeps TimeseriesChart mounted (fan-out eligible) even when the drawer is closed", async () => {
    render(<BottomDrawer gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.timeseries.mounted).toBe(true));

    useStore.getState().ui.setBottomDrawer("none");
    expect(useStore.getState().panels.timeseries.mounted).toBe(true);
  });

  it("the 'events' mode points to the tray in-register, never the admin-voice fallback", () => {
    useStore.getState().ui.setBottomDrawer("events");
    render(<BottomDrawer gameId={DEFAULT_GAME_ID} />);

    expect(screen.queryByText(/No events loaded yet\./)).not.toBeInTheDocument();
    expect(screen.getByText(/dispatch already runs in the tray/i)).toBeInTheDocument();
  });
});
