import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BottomStrip } from "./BottomStrip";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("BottomStrip", () => {
  it("defaults to the Time Series tab", async () => {
    render(<BottomStrip gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("timeseries-chart")).toBeInTheDocument());
  });

  it("switches to Events on click", async () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: { ...s.world.snapshot, events: [] } as never },
    }));
    render(<BottomStrip gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByRole("button", { name: "Events" }));
    expect(useStore.getState().ui.activeDockTab).toBe("events");
  });

  it("collapsing does not unmount the timeseries panel (keeps fan-out eligibility)", async () => {
    render(<BottomStrip gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.timeseries.mounted).toBe(true));

    await userEvent.click(screen.getByRole("button", { name: "▼" }));
    expect(useStore.getState().ui.bottomStripCollapsed).toBe(true);
    expect(useStore.getState().panels.timeseries.mounted).toBe(true);
  });
});
