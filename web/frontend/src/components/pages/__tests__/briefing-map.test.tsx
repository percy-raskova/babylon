/**
 * Briefing map promotion (spec-091 US2 / FR-004).
 *
 * The Situation-Map panel must render the live deck.gl map fed by the
 * snapshot — not the SVG `HexMapPlaceholder` stub. RED-first: these assert
 * the promoted behaviour before BriefingPage is wired.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { seedGameStore, resetGameStore } from "@/__tests__/helpers/seedSnapshot";
import { BriefingPage } from "@/components/pages/BriefingPage";

function renderBriefing() {
  return render(
    <MemoryRouter initialEntries={["/games/g1"]}>
      <Routes>
        <Route path="/games/:id" element={<BriefingPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  seedGameStore();
});

afterEach(() => {
  resetGameStore();
});

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
    for (const label of ["RENT", "CON", "SOL", "HEAT", "WEALTH", "BIOCAP"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
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
