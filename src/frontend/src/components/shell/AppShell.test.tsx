/**
 * Shell smoke test (spec-110 B3 stage 2) — all five cockpit regions
 * render with the real (module-singleton) zustand store; no React
 * context provider is needed since `useStore` requires none.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppShell } from "./AppShell";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("AppShell", () => {
  it("renders the five named cockpit regions", () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("region-statusbar")).toBeInTheDocument();
    expect(screen.getByTestId("region-outliner")).toBeInTheDocument();
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
    expect(screen.getByTestId("region-dock")).toBeInTheDocument();
    expect(screen.getByTestId("region-bottomstrip")).toBeInTheDocument();
  });

  it("mounts the tick-driven docked panels the fetch orchestrator fans out to", () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);
    // summary (StatusBar), communities + map (Outliner/MapPanel), timeseries (BottomStrip).
    expect(screen.getByTestId("time-controls")).toBeInTheDocument();
    expect(screen.getByTestId("action-composer")).toBeInTheDocument();
  });
});
