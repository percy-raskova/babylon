/**
 * Integration test: inspector ↔ UI store selection routing.
 *
 * Tests that store selections drive Inspector content.
 * Inspector now uses Breadcrumbs (with "Overview" button) instead of "Clear".
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Inspector } from "@/components/inspector/Inspector";
import { useUIStore } from "@/stores/uiStore";
import { makeSnapshot } from "@/test/fixtures";

describe("inspector selection routing", () => {
  const snapshot = makeSnapshot();

  it("shows OrgDashboard when nothing selected", () => {
    render(<Inspector snapshot={snapshot} />);
    // OrgDashboard shows the org list
    expect(screen.getByText("Workers Union")).toBeInTheDocument();
  });

  it("switches to NodeInspector when node selected via store", () => {
    useUIStore.setState({ selectedNodeId: "entity-proletariat" });
    render(<Inspector snapshot={snapshot} />);
    // Unique to entity detail — breadcrumbs also show "Proletariat"
    expect(screen.getByText("P(Acquiescence)")).toBeInTheDocument();
  });

  it("switches to HexInspector when hex selected via store", () => {
    useUIStore.setState({ selectedHexId: "territory-downtown" });
    render(<Inspector snapshot={snapshot} />);
    // "Downtown" may appear in breadcrumbs + inspector
    expect(screen.getAllByText("Downtown").length).toBeGreaterThanOrEqual(1);
  });

  it("node selection takes priority over hex selection", () => {
    useUIStore.setState({
      selectedNodeId: "entity-proletariat",
      selectedHexId: "territory-downtown",
    });
    render(<Inspector snapshot={snapshot} />);
    // P(Acquiescence) is unique to entity detail view
    expect(screen.getByText("P(Acquiescence)")).toBeInTheDocument();
  });

  it("overview button returns to OrgDashboard", async () => {
    const user = userEvent.setup();
    useUIStore.setState({
      selectedNodeId: "entity-proletariat",
      breadcrumbs: [
        {
          entityType: "entity",
          entityId: "entity-proletariat",
          displayName: "Proletariat",
          lensId: "political",
        },
      ],
    });
    render(<Inspector snapshot={snapshot} />);

    expect(screen.getByText("P(Acquiescence)")).toBeInTheDocument();
    await user.click(screen.getByText("Overview"));

    // After clearing, should reset selection
    expect(useUIStore.getState().selectedNodeId).toBeNull();
  });
});
