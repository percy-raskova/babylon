import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { MapRoute } from "./MapRoute";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("MapRoute", () => {
  it("resolves :id and renders the AppShell", async () => {
    render(
      <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}`]}>
        <Routes>
          <Route path="/game/:id" element={<MapRoute />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("region-statusbar")).toBeInTheDocument());
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
  });
});
