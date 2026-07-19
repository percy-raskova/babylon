import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { CircuitRoute } from "./CircuitRoute";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("CircuitRoute", () => {
  it("resolves :id and renders the CircuitPage, mounting the relocated ScissorsChart", async () => {
    render(
      <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}/circuit`]}>
        <Routes>
          <Route path="/game/:id/circuit" element={<CircuitRoute />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("region-circuit")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("scissors-chart")).toBeInTheDocument());
  });
});
