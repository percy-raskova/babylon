/**
 * Shell smoke test — rewritten for the 3-layer composition (architecture
 * §0/§1.1): Layer 0 MapStage (full-bleed, always mounted), Layer 1 chrome
 * overlay (`pointer-events-none` container whose children individually
 * re-enable `pointer-events-auto`), Layer 2 TakeoverOverlay. All with the
 * real (module-singleton) zustand store; no React context provider is
 * needed since `useStore` requires none.
 *
 * Wrapped in `MemoryRouter` (Track 2 T2-0): AppShell mounts TopBar, whose
 * "Circuit" nav button uses `useNavigate` — every render needs router
 * context now.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { AppShell } from "./AppShell";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function renderShell(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}`]}>
      <AppShell gameId={DEFAULT_GAME_ID} />
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("mounts Layer 0 MapStage full-bleed (absolute inset-0)", () => {
    renderShell();
    const map = screen.getByTestId("region-map");
    expect(map).toBeInTheDocument();
    expect(map.className).toMatch(/\babsolute\b/);
    expect(map.className).toMatch(/\binset-0\b/);
  });

  it("mounts Layer 1 chrome as a pointer-events-none container", () => {
    renderShell();
    expect(screen.getByTestId("chrome-layer").className).toContain("pointer-events-none");
  });

  it("keeps every frozen testid present: region-map, region-statusbar, region-outliner, tick-value, time-status", () => {
    renderShell();
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
    expect(screen.getByTestId("region-statusbar")).toBeInTheDocument();
    expect(screen.getByTestId("region-outliner")).toBeInTheDocument();
    expect(screen.getByTestId("tick-value")).toBeInTheDocument();
    expect(screen.getByTestId("time-status")).toBeInTheDocument();
  });

  it("preserves the region-dock and region-bottomstrip successor landmarks (real-loop.spec.ts contract)", () => {
    renderShell();
    expect(screen.getByTestId("region-dock")).toBeInTheDocument();
    expect(screen.getByTestId("region-bottomstrip")).toBeInTheDocument();
  });

  it("mounts the tick-driven docked panels the fetch orchestrator fans out to", () => {
    renderShell();
    // summary (TopBar), communities + map (OutlinerOverlay/MapStage),
    // timeseries (BottomDrawer).
    expect(screen.getByTestId("time-status")).toBeInTheDocument();
    expect(screen.getByTestId("action-composer")).toBeInTheDocument();
  });

  it("keeps the map mounted underneath an open takeover overlay (Layer 2, spec-110 B5)", async () => {
    renderShell();
    expect(screen.queryByTestId("takeover-overlay")).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId("open-wire"));
    expect(screen.getByTestId("takeover-overlay")).toBeInTheDocument();
    // The overlay renders OVER the shell, not instead of it — every
    // persistent region (map included) stays in the DOM underneath.
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
    expect(screen.getByTestId("region-statusbar")).toBeInTheDocument();
  });
});
