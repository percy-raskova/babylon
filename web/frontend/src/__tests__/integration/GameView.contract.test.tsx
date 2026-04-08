/**
 * Integration test: Mock Frontend Contract Validation for Wayne County.
 *
 * Verifies that the GameView, ResourcePanel, TrapIndicator, and action affordability
 * all correctly interface with the backend contract via our MSW stateful mock server.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { GameShell } from "@/components/layout/GameShell";
import { resetMockState } from "@/test/handlers";
import { useGameStore } from "@/stores/gameStore";

/** Render GameShell inside a MemoryRouter. */
function renderApp(gameId = "wayne-county-001") {
  return render(
    <MemoryRouter initialEntries={[`/games/${gameId}`]}>
      <Routes>
        <Route
          path="/games/:id"
          element={<GameShell username="testplayer" onBack={() => {}} onLogout={() => {}} />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Wayne County Frontend Contract Validation", () => {
  beforeEach(() => {
    // Reset MSW fake state before each test
    resetMockState();
    useGameStore.getState().reset();
  });

  it("Step 1: Hydrates initial vanguard economy and traps successfully", async () => {
    renderApp();

    // Check successful extraction and rendering of vanguard resources
    await waitFor(() => {
      expect(screen.getByText("Cadre Labor")).toBeInTheDocument();
    });

    // The mock makes Cadre Labor 1.0, Sympathizer Labor 4.0, Budget 100.
    // Ensure they show up in the Resource Panel.
    expect(screen.getByText("1.0/1.0")).toBeInTheDocument(); // CL
    expect(screen.getByText("4.0/5.0")).toBeInTheDocument(); // SL
    expect(screen.getByText(/100\.0/)).toBeInTheDocument(); // Budget

    // Ensure TrapIndicator shows the default "safe" traps
    expect(screen.getByText(/Deviation Profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Liberal/i)).toBeInTheDocument();
    expect(screen.getByText(/Ultra-Left/i)).toBeInTheDocument();
  });

  it("Step 2: Correctly handles affordability rejections (400 Bad Request) from the engine", async () => {
    const user = userEvent.setup();
    renderApp();

    // Wait for interface to be ready. Select "Attack", which needs 2 CL, but we only have 1 in mock
    await waitFor(() => {
      expect(screen.getByText("Attack")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Attack"));

    // Target a node (e.g. C003)
    await waitFor(() => {
      expect(screen.getByText("Select Target")).toBeInTheDocument();
    });

    // Find the elements safely. We just need to click any target.
    // The target selector might show C003
    const tbs = await screen.findAllByText(/Bourgeoisie/i);
    const firstTb = tbs[0];
    if (!firstTb) throw new Error("Missing target");
    await user.click(firstTb);

    // Proceed to submit Action
    await waitFor(() => {
      expect(screen.getByText("Submit Action")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Submit Action"));

    // Wait for the rejection from MSW ("Insufficient Cadre Labor (need 2)")
    // GameShell displays useGameStore.error automatically.
    await waitFor(() => {
      expect(screen.getByText(/Insufficient Cadre/i)).toBeInTheDocument();
    });

    // Verify CL was NOT deducted after rejection
    expect(screen.getByText("1.0/1.0")).toBeInTheDocument(); // CL is still 1.0!
  });

  it("Step 3: Correctly drives trap escalation over multiple actions and ticks", async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByText("Educate")).toBeInTheDocument();
    });

    // Do two "Educate" actions. Budget starts at $100. Educate costs $50 each.
    for (let i = 0; i < 2; i++) {
      await user.click(screen.getByText("Educate"));
      const t = await screen.findAllByText(/Proletariat/i);
      const firstT = t[0];
      if (!firstT) throw new Error("Missing target");
      await user.click(firstT); // target

      await waitFor(() => screen.getByText("Submit Action"));
      await user.click(screen.getByText("Submit Action"));

      // Wait for it to clear. (The UI replaces 'Submit Action' with 'Resolving...' briefly then returns)
      await waitFor(() => {
        expect(screen.queryByText("Submit Action")).toBeNull();
      });
    }

    // Resolve the tick!
    await user.click(screen.getByText("Resolve Tick"));

    // Wait for tick 6 (mock starts at tick 5)
    await waitFor(() => {
      expect(screen.getByText("6")).toBeInTheDocument(); // Top bar tick counter
    });

    // Check if traps escalated! The mock adds 0.3 Liberal score per 'educate' (total 0.6).
    // The test mock escalates liberal severity to 'moderate' when score > 0.5.
    // Trap Indicator renders 'severity-[type]'
    // Search for the word 'moderate' near 'Liberal'
    const trapTitle = screen.getByText(/Deviation Profile/i);
    const trapContainer = trapTitle.closest("div");
    if (!trapContainer) throw new Error("Missing container");
    expect(trapContainer.textContent).toMatch(/Liberal Moderate/i);

    // Budget should now be 0 since both educates succeeded.
    // The UI formats it as $0.0 or 0.0 or $0
    expect(screen.getByText(/0\.0/)).toBeInTheDocument();
  });
});
