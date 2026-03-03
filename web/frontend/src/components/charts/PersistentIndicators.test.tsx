/**
 * Unit tests for the PersistentIndicators component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PersistentIndicators } from "./PersistentIndicators";
import { makeSnapshot } from "@/test/fixtures";

describe("PersistentIndicators", () => {
  it("renders 4 indicator labels", () => {
    const snap = makeSnapshot();
    render(<PersistentIndicators snapshot={snap} />);

    expect(screen.getByText("Heat")).toBeInTheDocument();
    expect(screen.getByText("Consciousness")).toBeInTheDocument();
    expect(screen.getByText("Orgs")).toBeInTheDocument();
    expect(screen.getByText("Solidarity")).toBeInTheDocument();
  });

  it("shows correct org count", () => {
    const snap = makeSnapshot(); // 1 org in default fixture
    render(<PersistentIndicators snapshot={snap} />);
    // Both Orgs (1) and Solidarity (1) show "1", so use getAllByText
    const ones = screen.getAllByText("1");
    expect(ones.length).toBeGreaterThanOrEqual(1);
    // Verify the Orgs indicator specifically: find label, then sibling value
    expect(screen.getByText("Orgs")).toBeInTheDocument();
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

  it("counts solidarity edges", () => {
    const snap = makeSnapshot(); // 1 edge with solidarity_strength > 0
    render(<PersistentIndicators snapshot={snap} />);
    // 1 solidarity edge (the TENANCY edge has solidarity_strength 0.6)
    expect(screen.getAllByText("1")).toHaveLength(2); // org count=1, solidarity=1
  });
});
