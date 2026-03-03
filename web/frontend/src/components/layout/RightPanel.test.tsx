/**
 * Unit tests for the RightPanel component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RightPanel } from "./RightPanel";
import { useUIStore } from "@/stores/uiStore";

describe("RightPanel", () => {
  it("renders children when open", () => {
    render(
      <RightPanel>
        <div>Panel Content</div>
      </RightPanel>,
    );
    expect(screen.getByText("Panel Content")).toBeInTheDocument();
  });

  it("hides children when collapsed", () => {
    useUIStore.setState({ rightPanelOpen: false });
    render(
      <RightPanel>
        <div>Panel Content</div>
      </RightPanel>,
    );
    expect(screen.queryByText("Panel Content")).not.toBeInTheDocument();
  });

  it("toggle button collapses panel", async () => {
    const user = userEvent.setup();
    render(
      <RightPanel>
        <div>Panel Content</div>
      </RightPanel>,
    );

    await user.click(screen.getByTitle("Collapse sidebar"));
    expect(useUIStore.getState().rightPanelOpen).toBe(false);
    expect(screen.queryByText("Panel Content")).not.toBeInTheDocument();
  });

  it("toggle button expands panel", async () => {
    const user = userEvent.setup();
    useUIStore.setState({ rightPanelOpen: false });
    render(
      <RightPanel>
        <div>Panel Content</div>
      </RightPanel>,
    );

    await user.click(screen.getByTitle("Expand sidebar"));
    expect(useUIStore.getState().rightPanelOpen).toBe(true);
  });
});
