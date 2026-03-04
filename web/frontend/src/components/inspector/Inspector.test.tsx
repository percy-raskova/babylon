/**
 * Unit tests for the Inspector routing component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Inspector } from "./Inspector";
import { useUIStore } from "@/stores/uiStore";
import { makeSnapshot } from "@/test/fixtures";

describe("Inspector", () => {
  const snapshot = makeSnapshot();

  it("shows OrgDashboard when nothing selected", () => {
    render(<Inspector snapshot={snapshot} />);
    expect(screen.getByText("Organizations")).toBeInTheDocument();
  });

  it("shows NodeInspector when nodeId selected", () => {
    useUIStore.setState({ selectedNodeId: "entity-proletariat" });
    render(<Inspector snapshot={snapshot} />);
    // "Proletariat" may appear in breadcrumbs + inspector detail
    expect(screen.getAllByText("Proletariat").length).toBeGreaterThanOrEqual(1);
  });

  it("shows HexInspector when hexId selected", () => {
    useUIStore.setState({ selectedHexId: "territory-downtown" });
    render(<Inspector snapshot={snapshot} />);
    // "Downtown" may appear in breadcrumbs + inspector detail
    expect(screen.getAllByText("Downtown").length).toBeGreaterThanOrEqual(1);
  });

  it("node selection takes priority over hex selection", () => {
    useUIStore.setState({
      selectedNodeId: "entity-proletariat",
      selectedHexId: "territory-downtown",
    });
    render(<Inspector snapshot={snapshot} />);
    // Should show entity detail (P(Acquiescence) is unique to entity)
    expect(screen.getByText("P(Acquiescence)")).toBeInTheDocument();
  });

  it("overview button resets node selection", async () => {
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

    await user.click(screen.getByText("Overview"));
    expect(useUIStore.getState().selectedNodeId).toBeNull();
  });

  it("overview button resets hex selection", async () => {
    const user = userEvent.setup();
    useUIStore.setState({
      selectedHexId: "territory-downtown",
      breadcrumbs: [
        {
          entityType: "territory",
          entityId: "territory-downtown",
          displayName: "Downtown",
          lensId: "political",
        },
      ],
    });
    render(<Inspector snapshot={snapshot} />);

    await user.click(screen.getByText("Overview"));
    expect(useUIStore.getState().selectedHexId).toBeNull();
  });
});
