/**
 * Unit tests for the PersistentIndicators component.
 *
 * PersistentIndicators renders pinned indicators from uiStore using
 * IndicatorChip. Default pinned: avg_consciousness, avg_heat,
 * avg_organization, imperial_rent.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PersistentIndicators } from "./PersistentIndicators";
import { makeSnapshot } from "@/test/fixtures";

describe("PersistentIndicators", () => {
  it("renders default pinned indicator labels", () => {
    const snap = makeSnapshot();
    render(<PersistentIndicators snapshot={snap} />);

    // Default pinned: avg_consciousness, avg_heat, avg_organization, imperial_rent
    expect(screen.getByText("Avg Consciousness")).toBeInTheDocument();
    expect(screen.getByText("Avg Heat")).toBeInTheDocument();
    expect(screen.getByText("Avg Organization")).toBeInTheDocument();
    expect(screen.getByText("Imperial Rent")).toBeInTheDocument();
  });

  it("computes average heat correctly", () => {
    const snap = makeSnapshot(); // 2 territories: heat 0.4 and 0.1 -> avg 0.25
    render(<PersistentIndicators snapshot={snap} />);
    expect(screen.getByText("0.25")).toBeInTheDocument();
  });

  it("computes average consciousness correctly", () => {
    const snap = makeSnapshot(); // 2 entities: consciousness 0.3 and 0.1 -> avg 0.2
    render(<PersistentIndicators snapshot={snap} />);
    expect(screen.getByText("0.20")).toBeInTheDocument();
  });

  it("shows imperial rent value", () => {
    const snap = makeSnapshot(); // economy.imperial_rent = 50
    render(<PersistentIndicators snapshot={snap} />);
    expect(screen.getByText("$50.0")).toBeInTheDocument();
  });

  it("shows avg organization value", () => {
    const snap = makeSnapshot();
    render(<PersistentIndicators snapshot={snap} />);
    // Both entities have organization 0.15 -> avg = 0.15
    expect(screen.getByText("0.15")).toBeInTheDocument();
  });
});
