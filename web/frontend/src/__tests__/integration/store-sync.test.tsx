/**
 * Integration test: store ↔ component sync.
 *
 * Tests that Zustand store changes trigger component re-renders.
 *
 * Updated for Spec 052: no entities — consciousness from orgs, wealth from budgets.
 */

import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { Inspector } from "@/components/inspector/Inspector";
import { PersistentIndicators } from "@/components/charts/PersistentIndicators";
import { useUIStore } from "@/stores/uiStore";
import { makeSnapshot, makeOrg, makeTerritory, makeConsciousness } from "@/test/fixtures";

describe("store ↔ component sync", () => {
  it("UI store selection change re-renders Inspector", () => {
    const snapshot = makeSnapshot();
    const { rerender } = render(<Inspector snapshot={snapshot} />);

    // Initially shows OrgDashboard
    expect(screen.getByText("Workers Union")).toBeInTheDocument();

    // Set node selection in store — use org ID, not entity ID
    act(() => {
      useUIStore.setState({ selectedNodeId: "org-workers-union" });
    });
    rerender(<Inspector snapshot={snapshot} />);

    // Now shows org detail — consciousness section
    expect(screen.getByText("Revolutionary")).toBeInTheDocument();

    // Clear selection
    act(() => {
      useUIStore.setState({ selectedNodeId: null });
    });
    rerender(<Inspector snapshot={snapshot} />);

    // Back to OrgDashboard
    expect(screen.getAllByText("Workers Union").length).toBeGreaterThanOrEqual(1);
  });

  it("snapshot change updates PersistentIndicators", () => {
    const snap1 = makeSnapshot({
      organizations: [
        makeOrg({
          consciousness: makeConsciousness({ revolutionary: 0.5, liberal: 0.3, fascist: 0.2 }),
        }),
      ],
    });
    const { rerender } = render(<PersistentIndicators snapshot={snap1} />);
    expect(screen.getByText("0.50")).toBeInTheDocument();

    // Update with different consciousness values
    const snap2 = makeSnapshot({
      organizations: [
        makeOrg({
          consciousness: makeConsciousness({ revolutionary: 0.8, liberal: 0.15, fascist: 0.05 }),
        }),
      ],
    });
    rerender(<PersistentIndicators snapshot={snap2} />);
    expect(screen.getByText("0.80")).toBeInTheDocument();
  });

  it("territory count affects heat calculation", () => {
    const snap = makeSnapshot({
      territories: [
        makeTerritory({ id: "t1", heat: 0.6 }),
        makeTerritory({ id: "t2", heat: 0.8 }),
        makeTerritory({ id: "t3", heat: 1.0 }),
      ],
    });
    render(<PersistentIndicators snapshot={snap} />);
    // avg heat = (0.6 + 0.8 + 1.0) / 3 = 0.8
    expect(screen.getByText("0.80")).toBeInTheDocument();
  });
});
