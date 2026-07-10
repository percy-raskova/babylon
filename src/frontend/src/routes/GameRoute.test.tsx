import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { GameRoute } from "./GameRoute";
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
        <Route path="/game/:id" element={<GameRoute />} />
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

  it("renders the AppShell", async () => {
    renderGameRoute();
    await waitFor(() => expect(screen.getByTestId("region-statusbar")).toBeInTheDocument());
  });

  it("clears the active game id on unmount", async () => {
    const { unmount } = renderGameRoute();
    await waitFor(() => expect(useStore.getState().session.activeGameId).toBe(DEFAULT_GAME_ID));
    unmount();
    expect(useStore.getState().session.activeGameId).toBeNull();
  });
});
