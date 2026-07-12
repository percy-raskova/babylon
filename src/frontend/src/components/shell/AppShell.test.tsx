/**
 * Shell smoke test — rewritten for the 3-layer composition (architecture
 * §0/§1.1): Layer 0 MapStage (full-bleed, always mounted), Layer 1 chrome
 * overlay (`pointer-events-none` container whose children individually
 * re-enable `pointer-events-auto`), Layer 2 TakeoverOverlay. All with the
 * real (module-singleton) zustand store; no React context provider is
 * needed since `useStore` requires none.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "./AppShell";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("AppShell", () => {
  it("mounts Layer 0 MapStage full-bleed (absolute inset-0)", () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);
    const map = screen.getByTestId("region-map");
    expect(map).toBeInTheDocument();
    expect(map.className).toMatch(/\babsolute\b/);
    expect(map.className).toMatch(/\binset-0\b/);
  });

  it("mounts Layer 1 chrome as a pointer-events-none container", () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("chrome-layer").className).toContain("pointer-events-none");
  });

  it("keeps every frozen testid present: region-map, region-statusbar, region-outliner, tick-value, time-status", () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
    expect(screen.getByTestId("region-statusbar")).toBeInTheDocument();
    expect(screen.getByTestId("region-outliner")).toBeInTheDocument();
    expect(screen.getByTestId("tick-value")).toBeInTheDocument();
    expect(screen.getByTestId("time-status")).toBeInTheDocument();
  });

  it("preserves the region-dock and region-bottomstrip successor landmarks (real-loop.spec.ts contract)", () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("region-dock")).toBeInTheDocument();
    expect(screen.getByTestId("region-bottomstrip")).toBeInTheDocument();
  });

  it("mounts the tick-driven docked panels the fetch orchestrator fans out to", () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);
    // summary (TopBar), communities + map (OutlinerOverlay/MapStage),
    // timeseries (BottomDrawer).
    expect(screen.getByTestId("time-status")).toBeInTheDocument();
    expect(screen.getByTestId("action-composer")).toBeInTheDocument();
  });

  it("keeps the map mounted underneath an open takeover overlay (Layer 2, spec-110 B5)", async () => {
    render(<AppShell gameId={DEFAULT_GAME_ID} />);
    expect(screen.queryByTestId("takeover-overlay")).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId("open-wire"));
    expect(screen.getByTestId("takeover-overlay")).toBeInTheDocument();
    // The overlay renders OVER the shell, not instead of it — every
    // persistent region (map included) stays in the DOM underneath.
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
    expect(screen.getByTestId("region-statusbar")).toBeInTheDocument();
  });
});
