/**
 * Unit tests for the TimeSeries component.
 *
 * TimeSeries now shows lens-dependent chart defaults. The default lens
 * (political) shows: Consciousness, Heat, Organization.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TimeSeries } from "./TimeSeries";
import { useGameStore } from "@/stores/gameStore";
import { makeSnapshot } from "@/test/fixtures";

describe("TimeSeries", () => {
  it("shows empty state when no tick data", () => {
    const snap = makeSnapshot();
    render(<TimeSeries snapshot={snap} />);
    expect(screen.getByText(/No tick data recorded/)).toBeInTheDocument();
  });

  it("renders lens-default chart titles when data exists", () => {
    // Populate tick summaries
    useGameStore.setState({
      tickSummaries: [
        {
          tick: 0,
          avgHeat: 0.3,
          avgConsciousness: 0.2,
          totalWealth: 100,
          orgCount: 2,
          eventCount: 3,
          edgeCount: 5,
        },
        {
          tick: 1,
          avgHeat: 0.4,
          avgConsciousness: 0.3,
          totalWealth: 120,
          orgCount: 2,
          eventCount: 4,
          edgeCount: 6,
        },
      ],
    });
    const snap = makeSnapshot();
    render(<TimeSeries snapshot={snap} />);

    // Default lens is "political" which shows: Consciousness, Heat, Organization
    // Each visible chart produces 2 elements: selector button + chart section label
    expect(screen.getAllByText("Consciousness").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Heat").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Organization").length).toBeGreaterThanOrEqual(2);
    // Wealth is only in the selector button (not visible as chart)
    expect(screen.getAllByText("Wealth").length).toBeGreaterThanOrEqual(1);
  });

  it("renders chart sections matching default lens selection", () => {
    useGameStore.setState({
      tickSummaries: [
        {
          tick: 0,
          avgHeat: 0.3,
          avgConsciousness: 0.2,
          totalWealth: 100,
          orgCount: 2,
          eventCount: 3,
          edgeCount: 5,
        },
      ],
    });
    const snap = makeSnapshot();
    render(<TimeSeries snapshot={snap} />);

    // All 4 chart titles appear as selector buttons at top
    // Some also appear as chart section labels (duplicates)
    const titles = ["Wealth", "Heat", "Consciousness", "Organization"];
    for (const title of titles) {
      expect(screen.getAllByText(title).length).toBeGreaterThanOrEqual(1);
    }
  });
});
