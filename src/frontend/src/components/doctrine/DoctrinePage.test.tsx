import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { DoctrinePage } from "./DoctrinePage";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function renderDoctrinePage(): void {
  render(
    <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}/doctrine`]}>
      <Routes>
        <Route path="/game/:id" element={<div data-testid="stub-map">MAP</div>} />
        <Route path="/game/:id/doctrine" element={<DoctrinePage gameId={DEFAULT_GAME_ID} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("DoctrinePage", () => {
  it("renders the region-doctrine landmark and mounts the relocated DoctrineTakeover canvas", async () => {
    renderDoctrinePage();
    expect(screen.getByTestId("region-doctrine")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("doctrine-takeover")).toBeInTheDocument());
  });

  it("shows the tick from world.snapshot (kept live by the GameRoute layout's heartbeat)", () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: makeSnapshot({ tick: 9 }), lastTick: 9 },
    }));
    renderDoctrinePage();
    expect(screen.getByTestId("doctrine-tick-value")).toHaveTextContent("9");
  });

  it("shows 'no data' for tick when no snapshot has loaded yet", () => {
    renderDoctrinePage();
    expect(screen.getByTestId("doctrine-tick-value")).toHaveTextContent("no data");
  });

  it("navigates back to the map screen", async () => {
    renderDoctrinePage();
    await userEvent.click(screen.getByTestId("doctrine-back-to-map"));
    expect(screen.getByTestId("stub-map")).toBeInTheDocument();
  });
});
