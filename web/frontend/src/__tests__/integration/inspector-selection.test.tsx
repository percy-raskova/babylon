/**
 * Integration test: inspector ↔ UI store selection routing.
 *
 * Tests that store selections drive Inspector content.
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
    expect(screen.getByText("Proletariat")).toBeInTheDocument();
    expect(screen.getByText("P(Acquiescence)")).toBeInTheDocument();
  });

  it("switches to HexInspector when hex selected via store", () => {
    useUIStore.setState({ selectedHexId: "territory-downtown" });
    render(<Inspector snapshot={snapshot} />);
    expect(screen.getByText("Downtown")).toBeInTheDocument();
  });

  it("node selection takes priority over hex selection", () => {
    useUIStore.setState({
      selectedNodeId: "entity-proletariat",
      selectedHexId: "territory-downtown",
    });
    render(<Inspector snapshot={snapshot} />);
    // Should show entity, not territory
    expect(screen.getByText("Proletariat")).toBeInTheDocument();
    expect(screen.queryByText("Downtown")).not.toBeInTheDocument();
  });

  it("clear button returns to OrgDashboard", async () => {
    const user = userEvent.setup();
    useUIStore.setState({ selectedNodeId: "entity-proletariat" });
    render(<Inspector snapshot={snapshot} />);

    expect(screen.getByText("Proletariat")).toBeInTheDocument();
    await user.click(screen.getByText("Clear"));

    // After clearing, should show OrgDashboard
    expect(useUIStore.getState().selectedNodeId).toBeNull();
  });
});
