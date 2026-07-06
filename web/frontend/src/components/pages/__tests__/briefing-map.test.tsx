/**
 * Briefing map promotion (spec-091 US2 / FR-004) + lean-strip (Phase 6).
 *
 * The Situation-Map panel must render the live deck.gl map fed by the
 * snapshot — not the SVG `HexMapPlaceholder` stub.
 *
 * The two polling hooks are mocked so the render is deterministic and free of
 * unhandled fetch rejections (there is no backend / timeseries MSW handler in
 * jsdom); this isolates the test to BriefingPage's composition.
 */

import { describe, it, expect, vi } from "vitest";
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

// Imported after the mocks so BriefingPage picks up the mocked hooks.
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

describe("BriefingPage — first-class map", () => {
  it("mounts the live deck.gl map container", () => {
    renderBriefing();
    expect(screen.getByTestId("briefing-map")).toBeInTheDocument();
  });

  it("no longer renders the placeholder stub watermark", () => {
    renderBriefing();
    expect(screen.queryByText(/deck\.gl pending/i)).not.toBeInTheDocument();
  });
});

describe("BriefingPage — lean strip (course-correction Phase 6)", () => {
  it("renders the six-metric sparkline strip", () => {
    renderBriefing();
    for (const label of ["RENT", "CON", "SOL", "WEALTH", "BIOCAP"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    // "HEAT" also appears as the map's lens-mode button (spec-093
    // MapModeSelector) — no longer unique on this page.
    expect(screen.getAllByText("HEAT").length).toBeGreaterThan(0);
  });

  it("renders the End-Turn / Take-Actions call-to-action", () => {
    renderBriefing();
    expect(screen.getByRole("button", { name: /take actions/i })).toBeInTheDocument();
  });

  it("does not embed a verb action composer on Briefing", () => {
    renderBriefing();
    expect(screen.queryByText(/Compose Action/i)).not.toBeInTheDocument();
  });
});
