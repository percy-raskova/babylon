/**
 * Integration test: inspector ↔ UI store selection routing.
 *
 * Tests that store selections drive Inspector content.
 * Inspector now uses Breadcrumbs (with "Overview" button) instead of "Clear".
 *
 * Updated for Spec 052: no entity nodes — orgs and territories only.
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

  it("switches to NodeInspector when org selected via store", () => {
    useUIStore.setState({ selectedNodeId: "org-workers-union" });
    render(<Inspector snapshot={snapshot} />);
    // OrgDetail shows consciousness section
    expect(screen.getByText("Revolutionary")).toBeInTheDocument();
  });

  it("switches to HexInspector when hex selected via store", () => {
    useUIStore.setState({ selectedHexId: "territory-downtown" });
    render(<Inspector snapshot={snapshot} />);
    // "Downtown" may appear in breadcrumbs + inspector
    expect(screen.getAllByText("Downtown").length).toBeGreaterThanOrEqual(1);
  });

  it("node selection takes priority over hex selection", () => {
    useUIStore.setState({
      selectedNodeId: "org-workers-union",
      selectedHexId: "territory-downtown",
    });
    render(<Inspector snapshot={snapshot} />);
    // OrgDetail shows class character
    expect(screen.getByText("proletarian")).toBeInTheDocument();
  });

  it("overview button returns to OrgDashboard", async () => {
    const user = userEvent.setup();
    useUIStore.setState({
      selectedNodeId: "org-workers-union",
      breadcrumbs: [
        {
          entityType: "organization",
          entityId: "org-workers-union",
          displayName: "Workers Union",
          lensId: "political",
        },
      ],
    });
    render(<Inspector snapshot={snapshot} />);

    expect(screen.getByText("Revolutionary")).toBeInTheDocument();
    await user.click(screen.getByText("Overview"));

    // After clearing, should reset selection
    expect(useUIStore.getState().selectedNodeId).toBeNull();
  });
});
