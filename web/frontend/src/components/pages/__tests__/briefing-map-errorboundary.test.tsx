/**
 * Briefing map error boundary (spec-091 review fix #1).
 *
 * deck.gl is WebGL; a GPU/context init failure on the in-game INDEX route
 * (`/games/:id`) must degrade to the static placeholder, NOT white-screen the
 * page. This forces `DeckGLMap` to throw and asserts the graceful fallback.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

vi.mock("@/hooks/useGameState", async () => {
  const actual = await vi.importActual<typeof import("@/__tests__/helpers/seedSnapshot")>(
    "@/__tests__/helpers/seedSnapshot",
  );
  return {
    useGameState: () => ({ snapshot: actual.SEEDED_SNAPSHOT, loading: false, error: null }),
  };
});

vi.mock("@/hooks/useTimeseries", () => ({
  useTimeseries: () => ({
    data: {
      ticks: [],
      imperial_rent: [],
      consciousness: [],
      solidarity: [],
      heat: [],
      wealth: [],
      biocapacity: [],
    },
    loading: false,
    error: null,
    refresh: async () => {},
  }),
}));

// Force the deck.gl map to crash on render (simulating a WebGL init failure).
vi.mock("@/components/map/DeckGLMap", () => ({
  DeckGLMap: () => {
    throw new Error("WebGL context could not be created");
  },
}));

const { BriefingPage } = await import("@/components/pages/BriefingPage");

function renderBriefing() {
  return render(
    <MemoryRouter initialEntries={["/games/g1"]}>
      <Routes>
        <Route path="/games/:id" element={<BriefingPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("BriefingPage — map error boundary", () => {
  // The boundary logs the caught error via console.error; silence it here.
  beforeEach(() => vi.spyOn(console, "error").mockImplementation(() => {}));
  afterEach(() => vi.restoreAllMocks());

  it("degrades to the static placeholder when the deck.gl map throws", () => {
    renderBriefing();
    // The page did not white-screen: the map region is still mounted…
    expect(screen.getByTestId("briefing-map")).toBeInTheDocument();
    // …and it now shows the placeholder fallback, not a blank/crashed route.
    expect(screen.getByText(/deck\.gl pending/i)).toBeInTheDocument();
    // The rest of the Briefing still renders (sparklines, CTA).
    expect(screen.getByRole("button", { name: /take actions/i })).toBeInTheDocument();
  });
});
