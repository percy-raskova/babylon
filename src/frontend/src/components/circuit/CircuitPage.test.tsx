import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { CircuitPage } from "./CircuitPage";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function renderCircuitPage(): void {
  render(
    <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}/circuit`]}>
      <Routes>
        <Route path="/game/:id" element={<div data-testid="stub-map">MAP</div>} />
        <Route path="/game/:id/circuit" element={<CircuitPage gameId={DEFAULT_GAME_ID} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CircuitPage", () => {
  it("renders the region-circuit landmark and mounts the relocated ScissorsChart", async () => {
    renderCircuitPage();
    expect(screen.getByTestId("region-circuit")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("scissors-chart")).toBeInTheDocument());
  });

  it("shows the tick from world.snapshot (kept live by the GameRoute layout's heartbeat)", () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: makeSnapshot({ tick: 9 }), lastTick: 9 },
    }));
    renderCircuitPage();
    expect(screen.getByTestId("circuit-tick-value")).toHaveTextContent("9");
  });

  it("shows 'no data' for tick when no snapshot has loaded yet", () => {
    renderCircuitPage();
    expect(screen.getByTestId("circuit-tick-value")).toHaveTextContent("no data");
  });

  it("navigates back to the map screen", async () => {
    renderCircuitPage();
    await userEvent.click(screen.getByTestId("circuit-back-to-map"));
    expect(screen.getByTestId("stub-map")).toBeInTheDocument();
  });

  it("mounts the MELT gauge and Fundamental Theorem meter on the instruments rail (T2-4/T2-6)", async () => {
    renderCircuitPage();
    expect(screen.getByTestId("circuit-instruments")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("melt-gauge")).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getByTestId("fundamental-theorem-meter")).toBeInTheDocument(),
    );
  });
});
