/**
 * Unit tests for the PersistentIndicators component.
 *
 * PersistentIndicators renders pinned indicators from uiStore using
 * IndicatorChip. Default pinned: avg_consciousness, avg_heat,
 * avg_organization, imperial_rent.
 *
 * Updated for Spec 052: consciousness from org revolutionary component,
 * organization from cadre_level, imperial_rent from derived block.
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
    // Default fixture: 1 org with consciousness.revolutionary = 0.85 -> avg 0.85
    const snap = makeSnapshot();
    render(<PersistentIndicators snapshot={snap} />);
    expect(screen.getByText("0.85")).toBeInTheDocument();
  });

  it("shows imperial rent value", () => {
    // derived.imperial_rent.total = 15.5
    const snap = makeSnapshot();
    render(<PersistentIndicators snapshot={snap} />);
    expect(screen.getByText("$15.5")).toBeInTheDocument();
  });

  it("shows avg organization value", () => {
    // 1 org with cadre_level = 0.35 -> avg = 0.35
    const snap = makeSnapshot();
    render(<PersistentIndicators snapshot={snap} />);
    expect(screen.getByText("0.35")).toBeInTheDocument();
  });
});
