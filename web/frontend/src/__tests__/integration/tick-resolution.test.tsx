/**
 * Integration test: tick resolution flow (v2).
 *
 * Tests the resolve tick → results display cycle through the v2 architecture.
 * Uses GameRouteShell + ResultsPage rather than the removed v1 GameShell.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { seedGameStore, resetGameStore } from "@/__tests__/helpers/seedSnapshot";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { ResultsPage } from "@/components/pages/ResultsPage";

beforeEach(() => {
  seedGameStore();
});

afterEach(() => {
  resetGameStore();
});

describe("tick resolution flow (v2)", () => {
  it("ResultsPage renders NPC org roster from the live snapshot", () => {
    render(
      <MemoryRouter initialEntries={["/games/game-001/results"]}>
        <Routes>
          <Route path="/games/:id/results" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>,
    );

    // Results page shows the NPC action section
    expect(screen.getByText("NPC Orgs")).toBeInTheDocument();
    // Shows the tick number from mock data
    expect(screen.getByText(/Tick/)).toBeInTheDocument();
  });

  it("ResultsPage renders player org section from the live snapshot", () => {
    render(
      <MemoryRouter initialEntries={["/games/game-001/results"]}>
        <Routes>
          <Route path="/games/:id/results" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Player Orgs")).toBeInTheDocument();
  });
});
