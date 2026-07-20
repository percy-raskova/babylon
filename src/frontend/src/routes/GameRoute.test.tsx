import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { GameRoute } from "./GameRoute";
import { MapRoute } from "./MapRoute";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

afterEach(() => {
  vi.useRealTimers();
});

function renderGameRoute(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}`]}>
      <Routes>
        <Route path="/game/:id" element={<GameRoute />}>
          <Route index element={<MapRoute />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("GameRoute", () => {
  it("sets the active game id and fetches initial state", async () => {
    renderGameRoute();
    expect(useStore.getState().session.activeGameId).toBe(DEFAULT_GAME_ID);
    await waitFor(() => expect(useStore.getState().world.snapshot).not.toBeNull());
  });

  it("renders the matched child route (Outlet) — the map screen by default", async () => {
    renderGameRoute();
    await waitFor(() => expect(screen.getByTestId("region-statusbar")).toBeInTheDocument());
  });

  it("clears the active game id on unmount", async () => {
    const { unmount } = renderGameRoute();
    await waitFor(() => expect(useStore.getState().session.activeGameId).toBe(DEFAULT_GAME_ID));
    unmount();
    expect(useStore.getState().session.activeGameId).toBeNull();
  });

  it("is a layout route: the session/heartbeat effect stays mounted across sibling screens", async () => {
    render(
      <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}/circuit`]}>
        <Routes>
          <Route path="/game/:id" element={<GameRoute />}>
            <Route index element={<MapRoute />} />
            <Route path="circuit" element={<div data-testid="stub-circuit">circuit</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    // GameRoute matched /game/:id and rendered its "circuit" child into the
    // Outlet — its own session-setup effect ran regardless of which child
    // matched (the whole point: switching screens never tears down the
    // heartbeat/activeGameId the way two independent top-level routes would).
    expect(useStore.getState().session.activeGameId).toBe(DEFAULT_GAME_ID);
    expect(screen.getByTestId("stub-circuit")).toBeInTheDocument();
  });
});
