/**
 * Unit tests for the BottomPanel component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BottomPanel } from "./BottomPanel";
import { useUIStore } from "@/stores/uiStore";

describe("BottomPanel", () => {
  it("renders children when open", () => {
    render(
      <BottomPanel>
        <div>Tab Content</div>
      </BottomPanel>,
    );
    expect(screen.getByText("Tab Content")).toBeInTheDocument();
  });

  it("hides children when collapsed", () => {
    useUIStore.setState({ bottomPanelOpen: false });
    render(
      <BottomPanel>
        <div>Tab Content</div>
      </BottomPanel>,
    );
    expect(screen.queryByText("Tab Content")).not.toBeInTheDocument();
  });

  it("renders tab buttons", () => {
    render(
      <BottomPanel>
        <div />
      </BottomPanel>,
    );
    expect(screen.getByText("Time Series")).toBeInTheDocument();
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.queryByText("Graph")).not.toBeInTheDocument();
  });

  it("clicking tab switches active tab", async () => {
    const user = userEvent.setup();
    render(
      <BottomPanel>
        <div />
      </BottomPanel>,
    );

    await user.click(screen.getByText("Events"));
    expect(useUIStore.getState().bottomTab).toBe("events");

    await user.click(screen.getByText("Notifications"));
    expect(useUIStore.getState().bottomTab).toBe("notifications");
  });

  it("toggle button collapses panel", async () => {
    const user = userEvent.setup();
    render(
      <BottomPanel>
        <div>Content</div>
      </BottomPanel>,
    );

    await user.click(screen.getByTitle("Collapse panel"));
    expect(useUIStore.getState().bottomPanelOpen).toBe(false);
  });
});
