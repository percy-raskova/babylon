import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DuelSparkline } from "./DuelSparkline";
import type { ClassHistoryPoint, RuptureMarker } from "@/types/game";

const points: ClassHistoryPoint[] = [
  { tick: 0, p_acquiescence: 0.8, p_revolution: 0.1 },
  { tick: 1, p_acquiescence: 0.6, p_revolution: 0.3 },
  { tick: 2, p_acquiescence: 0.4, p_revolution: 0.5 },
];

describe("DuelSparkline", () => {
  it("renders both the acquiescence and revolution series", () => {
    render(<DuelSparkline points={points} />);
    expect(screen.getByTestId("duel-sparkline")).toBeInTheDocument();
    expect(screen.getByTestId("duel-sparkline-acquiescence")).toBeInTheDocument();
    expect(screen.getByTestId("duel-sparkline-revolution")).toBeInTheDocument();
  });

  it("renders a rupture marker at a tick present in the history", () => {
    const markers: RuptureMarker[] = [{ tick: 1, eventId: "evt-uprising-1" }];
    render(<DuelSparkline points={points} markers={markers} />);
    expect(screen.getByTestId("duel-sparkline-marker-evt-uprising-1")).toBeInTheDocument();
  });

  it("skips a marker whose tick is not present in the history (no fabricated position)", () => {
    const markers: RuptureMarker[] = [{ tick: 99, eventId: "evt-orphan" }];
    render(<DuelSparkline points={points} markers={markers} />);
    expect(screen.queryByTestId("duel-sparkline-marker-evt-orphan")).not.toBeInTheDocument();
  });

  it("shows an honest empty state when there is no history yet", () => {
    render(<DuelSparkline points={[]} />);
    expect(screen.getByTestId("duel-sparkline-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("duel-sparkline")).not.toBeInTheDocument();
  });

  it("shows an honest no-values state when ticks exist but both series are null throughout", () => {
    const allNull: ClassHistoryPoint[] = [
      { tick: 0, p_acquiescence: null, p_revolution: null },
      { tick: 1, p_acquiescence: null, p_revolution: null },
    ];
    render(<DuelSparkline points={allNull} />);
    expect(screen.getByTestId("duel-sparkline-no-values")).toBeInTheDocument();
  });

  it("breaks the polyline into separate runs around a null gap (no fabricated interpolation)", () => {
    const withGap: ClassHistoryPoint[] = [
      { tick: 0, p_acquiescence: 0.8, p_revolution: 0.1 },
      { tick: 1, p_acquiescence: null, p_revolution: 0.3 },
      { tick: 2, p_acquiescence: 0.4, p_revolution: 0.5 },
    ];
    render(<DuelSparkline points={withGap} />);
    // Two runs either side of the null acquiescence point, each a single point.
    const runs = screen.getAllByTestId("duel-sparkline-acquiescence");
    expect(runs).toHaveLength(2);
  });
});
