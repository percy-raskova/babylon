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
    expect(screen.getByText("Proletariat")).toBeInTheDocument();
    expect(screen.getByText("Inspector")).toBeInTheDocument();
  });

  it("shows HexInspector when hexId selected", () => {
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

  it("clear button resets node selection", async () => {
    const user = userEvent.setup();
    useUIStore.setState({ selectedNodeId: "entity-proletariat" });
    render(<Inspector snapshot={snapshot} />);

    await user.click(screen.getByText("Clear"));
    expect(useUIStore.getState().selectedNodeId).toBeNull();
  });

  it("clear button resets hex selection", async () => {
    const user = userEvent.setup();
    useUIStore.setState({ selectedHexId: "territory-downtown" });
    render(<Inspector snapshot={snapshot} />);

    await user.click(screen.getByText("Clear"));
    expect(useUIStore.getState().selectedHexId).toBeNull();
  });
});
