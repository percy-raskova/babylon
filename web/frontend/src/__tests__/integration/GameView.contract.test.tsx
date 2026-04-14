/**
 * Integration test: Mock Frontend Contract Validation for Wayne County.
 *
 * These tests prove the frontend correctly interfaces with the backend
 * API contract. They run against the stateful MSW mock server which
 * simulates the Babylon engine's Wayne County scenario.
 *
 * Contract validated:
 * 1. VanguardResources renders in ResourcePanel from org.vanguard
 * 2. TrapIndicator hides when all traps are severity=none
 * 3. Affordability rejection (400) surfaces as an error message
 * 4. Tick resolution updates game state and escalates traps
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { GameShell } from "@/components/layout/GameShell";
import { resetMockState } from "@/test/handlers";
import { useGameStore } from "@/stores/gameStore";
import { makeWayneCountySnapshot } from "@/test/fixtures";

// Mock useGameState to read directly from zustand store (no polling)
vi.mock("@/hooks/useGameState", () => ({
  useGameState: (_gameId: string) => {
    const snapshot = useGameStore.getState().snapshot;
    const loading = useGameStore.getState().loading;
    const error = useGameStore.getState().error;
    return {
      snapshot,
      available: useGameStore.getState().available,
      loading,
      error,
      submitAction: vi.fn().mockResolvedValue(undefined),
      resolveTick: vi.fn().mockResolvedValue([]),
      refresh: vi.fn().mockResolvedValue(undefined),
    };
  },
}));

/** Render GameShell pre-seeded with Wayne County snapshot. */
function renderWithWayneCounty(overrides?: Parameters<typeof makeWayneCountySnapshot>[0]) {
  const snapshot = makeWayneCountySnapshot(overrides);
  useGameStore.setState({ snapshot, loading: false, error: null });

  return render(
    <MemoryRouter initialEntries={["/games/wayne-county-001"]}>
      <Routes>
        <Route
          path="/games/:id"
          element={<GameShell username="testplayer" onBack={() => {}} onLogout={() => {}} />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Wayne County Frontend Contract", () => {
  beforeEach(() => {
    resetMockState();
    useGameStore.getState().reset();
  });

  afterEach(() => {
    cleanup();
  });

  describe("Contract 1: VanguardResources hydration", () => {
    it("renders resource panel with CL, SL, REP, $$$, and HEAT labels", () => {
      renderWithWayneCounty();

      // ResourcePanel renders these header labels
      expect(screen.getByText("CL")).toBeInTheDocument();
      expect(screen.getByText("SL")).toBeInTheDocument();
      expect(screen.getByText("REP")).toBeInTheDocument();
      expect(screen.getByText("$$$")).toBeInTheDocument();
      expect(screen.getByText("HEAT")).toBeInTheDocument();
    });

    it("displays correct vanguard values from mock fixture", () => {
      renderWithWayneCounty();

      // Mock fixture: CL=1.0, SL=4.0, REP=0, Budget=$100, Heat=0
      // ResourceGauge renders value.toFixed(1) -> "1.0", "4.0"
      // ResourceStat renders budget as `$${v.budget.toFixed(0)}` -> "$100"
      // ResourceStat renders rep as `${(v.reputation * 100).toFixed(0)}%` -> "0%"
      expect(screen.getByText("1.0")).toBeInTheDocument(); // CL
      expect(screen.getByText("4.0")).toBeInTheDocument(); // SL
      expect(screen.getByText("$100")).toBeInTheDocument(); // Budget
    });

    it("shows org name and type in resource panel header", () => {
      renderWithWayneCounty();

      // Name appears in both ResourcePanel header and ActionComposer org pill
      expect(
        screen.getAllByText("Wayne County Organizing Committee").length,
      ).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("civil_society_org").length).toBeGreaterThanOrEqual(1);
    });

    it("falls back to basic display when vanguard is undefined", () => {
      renderWithWayneCounty({
        organizations: [
          {
            id: "ORG001",
            name: "Test Org",
            org_type: "civil_society_org",
            class_character: "proletarian",
            cohesion: 0.5,
            cadre_level: 0.1,
            budget: 100,
            heat: 0,
            territory_ids: [],
            hyperedge_memberships: [],
            consciousness: { liberal: 0.05, fascist: 0.02, revolutionary: 0.93 },
            ooda: { observe: 0.6, orient: 0.5, decide: 0.7, act: 0.8, cycle_ticks: 1 },
            vanguard: undefined,
          },
        ],
      });

      // Without vanguard, ResourcePanel shows basic Budget/Cadre/Heat
      // "Budget" may appear in multiple places (ResourcePanel + ActionComposer org pill)
      expect(screen.getAllByText("Budget").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Cadre")).toBeInTheDocument();
      // CL/SL/REP should NOT be present
      expect(screen.queryByText("CL")).not.toBeInTheDocument();
    });
  });

  describe("Contract 2: TrapIndicator behavior", () => {
    it("hides trap warnings when all traps are severity=none (tick 0)", () => {
      renderWithWayneCounty();

      // TrapIndicator returns null when active_trap is null
      expect(screen.queryByText(/Liberal Deviation/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Ultra-Left Deviation/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Rightist Deviation/)).not.toBeInTheDocument();
    });

    it("shows liberal deviation warning when trap is escalated", () => {
      renderWithWayneCounty({
        traps: {
          liberal: {
            severity: "moderate",
            score: 0.6,
            indicators: ["Excessive electoral focus"],
            ticks_at_moderate: 2,
          },
          ultra_left: {
            severity: "none",
            score: 0.1,
            indicators: [],
            ticks_at_moderate: 0,
          },
          rightist: {
            severity: "none",
            score: 0.0,
            indicators: [],
            ticks_at_moderate: 0,
          },
          active_trap: "liberal",
          game_over_trap: null,
        },
      });

      expect(screen.getByText(/Liberal Deviation/)).toBeInTheDocument();
      expect(screen.getByText(/moderate/i)).toBeInTheDocument();
      expect(screen.getByText(/reformism/i)).toBeInTheDocument(); // warning text
    });

    it("shows game over message for severe ultra-left trap", () => {
      renderWithWayneCounty({
        traps: {
          liberal: {
            severity: "none",
            score: 0.0,
            indicators: [],
            ticks_at_moderate: 0,
          },
          ultra_left: {
            severity: "severe",
            score: 1.0,
            indicators: [],
            ticks_at_moderate: 5,
          },
          rightist: {
            severity: "none",
            score: 0.0,
            indicators: [],
            ticks_at_moderate: 0,
          },
          active_trap: "ultra_left",
          game_over_trap: "ultra_left",
        },
      });

      expect(screen.getByText(/Ultra-Left Deviation/)).toBeInTheDocument();
      expect(screen.getByText(/adventurist tactics/i)).toBeInTheDocument();
    });
  });

  describe("Contract 3: Error display", () => {
    it("surfaces affordability rejection error in the error banner", () => {
      const snapshot = makeWayneCountySnapshot();
      useGameStore.setState({
        snapshot,
        loading: false,
        error: "Insufficient Cadre Labor (need 2)",
      });

      render(
        <MemoryRouter initialEntries={["/games/wayne-county-001"]}>
          <Routes>
            <Route
              path="/games/:id"
              element={<GameShell username="testplayer" onBack={() => {}} onLogout={() => {}} />}
            />
          </Routes>
        </MemoryRouter>,
      );

      const errorBanner = screen.getByTestId("error-banner");
      expect(errorBanner).toBeInTheDocument();
      expect(errorBanner.textContent).toContain("Insufficient Cadre Labor");
    });
  });

  describe("Contract 4: Store-level MSW integration", () => {
    it("fetches Wayne County snapshot from MSW and populates store", async () => {
      // Use the REAL fetchState (not mocked) to hit MSW
      await useGameStore.getState().fetchState("wayne-county-001");

      const snapshot = useGameStore.getState().snapshot;
      expect(snapshot).not.toBeNull();
      expect(snapshot!.session_id).toBe("wayne-county-001");
      expect(snapshot!.organizations).toHaveLength(1);
      expect(snapshot!.organizations[0]!.name).toBe("Wayne County Organizing Committee");
      expect(snapshot!.organizations[0]!.vanguard).not.toBeNull();
      expect(snapshot!.organizations[0]!.vanguard!.cadre_labor).toBe(1.0);
    });

    it("submitAction with unaffordable verb sets error in store via MSW 400", async () => {
      // Pre-fetch state first
      await useGameStore.getState().fetchState("wayne-county-001");

      // Submit unaffordable attack (CL=1, needs 2)
      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "attack",
        target_id: "C003",
      });

      // Store should have the error from MSW
      const error = useGameStore.getState().error;
      expect(error).toContain("Insufficient Cadre Labor");
    });

    it("submitAction with affordable verb deducts resources via MSW", async () => {
      // Pre-fetch
      await useGameStore.getState().fetchState("wayne-county-001");

      // Submit affordable educate (budget=100, costs 50)
      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "educate",
        target_id: "C001",
      });

      // Re-fetch and check budget
      const snapshot = useGameStore.getState().snapshot;
      expect(snapshot).not.toBeNull();
      expect(snapshot!.organizations[0]!.vanguard!.budget).toBe(50);
    });

    it("resolveTick advances tick and escalates traps via MSW", async () => {
      // Pre-fetch
      await useGameStore.getState().fetchState("wayne-county-001");

      // Submit 2 educates to get liberal score > 0.5
      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "educate",
        target_id: "C001",
      });
      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "educate",
        target_id: "C001",
      });

      // Resolve tick
      await useGameStore.getState().resolveTick("wayne-county-001");

      // Store should have updated snapshot
      const snapshot = useGameStore.getState().snapshot;
      expect(snapshot).not.toBeNull();
      expect(snapshot!.tick).toBeGreaterThanOrEqual(1);
      expect(snapshot!.traps).toBeDefined();
      expect(snapshot!.traps!.liberal.score).toBeGreaterThan(0.5);
      expect(snapshot!.traps!.liberal.severity).toBe("moderate");
      expect(snapshot!.traps!.active_trap).toBe("liberal");
    });
  });
});
