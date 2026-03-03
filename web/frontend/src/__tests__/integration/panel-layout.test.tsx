/**
 * Integration test: panel layout interactions.
 *
 * Tests right panel collapse/expand, bottom panel tab switching,
 * and content visibility changes.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RightPanel } from "@/components/layout/RightPanel";
import { BottomPanel } from "@/components/layout/BottomPanel";
import { useUIStore } from "@/stores/uiStore";

describe("panel layout interactions", () => {
  describe("right panel", () => {
    it("collapse hides content and expand shows it", async () => {
      const user = userEvent.setup();
      render(
        <RightPanel>
          <div>Inspector Content</div>
        </RightPanel>,
      );

      expect(screen.getByText("Inspector Content")).toBeInTheDocument();

      // Collapse
      await user.click(screen.getByTitle("Collapse sidebar"));
      expect(screen.queryByText("Inspector Content")).not.toBeInTheDocument();
      expect(useUIStore.getState().rightPanelOpen).toBe(false);

      // Expand
      await user.click(screen.getByTitle("Expand sidebar"));
      expect(screen.getByText("Inspector Content")).toBeInTheDocument();
      expect(useUIStore.getState().rightPanelOpen).toBe(true);
    });
  });

  describe("bottom panel", () => {
    it("tab switching updates store and content visibility", async () => {
      const user = userEvent.setup();
      render(
        <BottomPanel>
          <div>Tab Content</div>
        </BottomPanel>,
      );

      // Default tab is timeseries
      expect(useUIStore.getState().bottomTab).toBe("timeseries");

      // Switch to events
      await user.click(screen.getByText("Events"));
      expect(useUIStore.getState().bottomTab).toBe("events");

      // Switch to graph
      await user.click(screen.getByText("Graph"));
      expect(useUIStore.getState().bottomTab).toBe("graph");

      // Switch back to time series
      await user.click(screen.getByText("Time Series"));
      expect(useUIStore.getState().bottomTab).toBe("timeseries");
    });

    it("collapse hides content and tab area", async () => {
      const user = userEvent.setup();
      render(
        <BottomPanel>
          <div>Chart Content</div>
        </BottomPanel>,
      );

      expect(screen.getByText("Chart Content")).toBeInTheDocument();

      await user.click(screen.getByTitle("Collapse panel"));
      expect(screen.queryByText("Chart Content")).not.toBeInTheDocument();
      expect(useUIStore.getState().bottomPanelOpen).toBe(false);
    });
  });
});
