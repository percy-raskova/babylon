/**
 * Unit tests for the TimeSeries component.
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

  it("renders chart titles when data exists", () => {
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

    expect(screen.getByText("Wealth")).toBeInTheDocument();
    expect(screen.getByText("Heat")).toBeInTheDocument();
    expect(screen.getByText("Consciousness")).toBeInTheDocument();
    expect(screen.getByText("Organization")).toBeInTheDocument();
  });

  it("renders 4 chart sections", () => {
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

    const titles = ["Wealth", "Heat", "Consciousness", "Organization"];
    for (const title of titles) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
  });
});
