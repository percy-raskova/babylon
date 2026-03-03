/**
 * Integration test: store ↔ component sync.
 *
 * Tests that Zustand store changes trigger component re-renders.
 */

import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { Inspector } from "@/components/inspector/Inspector";
import { PersistentIndicators } from "@/components/charts/PersistentIndicators";
import { useUIStore } from "@/stores/uiStore";
import { makeSnapshot, makeEntity, makeTerritory } from "@/test/fixtures";

describe("store ↔ component sync", () => {
  it("UI store selection change re-renders Inspector", () => {
    const snapshot = makeSnapshot();
    const { rerender } = render(<Inspector snapshot={snapshot} />);

    // Initially shows OrgDashboard
    expect(screen.getByText("Workers Union")).toBeInTheDocument();

    // Set node selection in store
    act(() => {
      useUIStore.setState({ selectedNodeId: "entity-proletariat" });
    });
    rerender(<Inspector snapshot={snapshot} />);

    // Now shows entity detail
    expect(screen.getByText("Proletariat")).toBeInTheDocument();

    // Clear selection
    act(() => {
      useUIStore.setState({ selectedNodeId: null });
    });
    rerender(<Inspector snapshot={snapshot} />);

    // Back to OrgDashboard
    expect(screen.getByText("Workers Union")).toBeInTheDocument();
  });

  it("snapshot change updates PersistentIndicators", () => {
    const snap1 = makeSnapshot({
      entities: [
        makeEntity({ consciousness: 0.5 }),
        makeEntity({ id: "entity-bourgeoisie", consciousness: 0.5 }),
      ],
    });
    const { rerender } = render(<PersistentIndicators snapshot={snap1} />);
    expect(screen.getByText("0.50")).toBeInTheDocument();

    // Update with different consciousness values
    const snap2 = makeSnapshot({
      entities: [
        makeEntity({ consciousness: 0.8 }),
        makeEntity({ id: "entity-bourgeoisie", consciousness: 0.8 }),
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
