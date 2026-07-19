import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Routes, Route } from "react-router";
import { server } from "@/test/server";
import { CircuitPage } from "./CircuitPage";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot, makeEconomyDashboardPayload } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function mockEconomy(overrides: Parameters<typeof makeEconomyDashboardPayload>[0]): void {
  server.use(
    http.get("/api/games/:id/economy/", () =>
      HttpResponse.json({ status: "ok", data: makeEconomyDashboardPayload(overrides) }),
    ),
  );
}

function renderCircuitPage(): void {
  render(
    <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}/circuit`]}>
      <Routes>
        <Route path="/game/:id" element={<div data-testid="stub-map">MAP</div>} />
        <Route
          path="/game/:id/doctrine"
          element={<div data-testid="stub-doctrine">DOCTRINE</div>}
        />
        <Route path="/game/:id/circuit" element={<CircuitPage gameId={DEFAULT_GAME_ID} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CircuitPage", () => {
  it("renders the region-circuit landmark and mounts the relocated ScissorsChart", async () => {
    renderCircuitPage();
    expect(screen.getByTestId("region-circuit")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("scissors-chart")).toBeInTheDocument());
  });

  it("shows the tick from world.snapshot (kept live by the GameRoute layout's heartbeat)", () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: makeSnapshot({ tick: 9 }), lastTick: 9 },
    }));
    renderCircuitPage();
    expect(screen.getByTestId("circuit-tick-value")).toHaveTextContent("9");
  });

  it("shows 'no data' for tick when no snapshot has loaded yet", () => {
    renderCircuitPage();
    expect(screen.getByTestId("circuit-tick-value")).toHaveTextContent("no data");
  });

  it("navigates back to the map screen", async () => {
    renderCircuitPage();
    await userEvent.click(screen.getByTestId("circuit-back-to-map"));
    expect(screen.getByTestId("stub-map")).toBeInTheDocument();
  });

  it("mounts the MELT gauge and Fundamental Theorem meter on the instruments rail (T2-4/T2-6)", async () => {
    renderCircuitPage();
    expect(screen.getByTestId("circuit-instruments")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("melt-gauge")).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getByTestId("fundamental-theorem-meter")).toBeInTheDocument(),
    );
  });

  it("renders the wealth-by-class-role composition (T2-7 relocation)", async () => {
    mockEconomy({
      wealth_by_class_role: { periphery_proletariat: 40, core_bourgeoisie: 60 },
    });
    renderCircuitPage();
    await waitFor(() => expect(screen.getByTestId("breakdown-bar")).toBeInTheDocument());
    expect(screen.getByText("Periphery Proletariat")).toBeInTheDocument();
    expect(screen.getByText("Core Bourgeoisie")).toBeInTheDocument();
  });

  describe("the Veil of Money (T2-8/T2-9)", () => {
    it("tier 0: veils both the exploitation axis and the scissors, naming the tier-1 study target", async () => {
      mockEconomy({
        veil: {
          tier: 0,
          next_unlock_node_id: "class_consciousness",
          next_unlock_label: "Class Consciousness",
          value_produced: null,
          exploitation_rate: null,
        },
      });
      renderCircuitPage();
      await waitFor(() => expect(screen.getAllByTestId("veil-locked")).toHaveLength(2));
      expect(screen.queryByTestId("scissors-chart")).not.toBeInTheDocument();
      expect(screen.queryByTestId("circuit-exploitation-chips")).not.toBeInTheDocument();
      expect(screen.getAllByText(/Study: Class Consciousness/)).toHaveLength(2);
    });

    it("tier 1: exploitation axis unlocked with real numbers, scissors still veiled naming trade_unionism", async () => {
      mockEconomy({
        veil: {
          tier: 1,
          next_unlock_node_id: "trade_unionism",
          next_unlock_label: "Trade Unionism",
          value_produced: 100,
          exploitation_rate: 0.2,
        },
      });
      renderCircuitPage();
      await waitFor(() =>
        expect(screen.getByTestId("circuit-exploitation-chips")).toBeInTheDocument(),
      );
      expect(screen.getByTestId("stat-value produced")).toHaveTextContent("100");
      expect(screen.getByTestId("stat-exploitation rate")).toHaveTextContent("0.200");
      expect(screen.queryByTestId("scissors-chart")).not.toBeInTheDocument();
      expect(screen.getByText(/Study: Trade Unionism/)).toBeInTheDocument();
    });

    it("tier 2 (default fixture): both the exploitation axis and the scissors are unlocked", async () => {
      renderCircuitPage();
      await waitFor(() =>
        expect(screen.getByTestId("circuit-exploitation-chips")).toBeInTheDocument(),
      );
      await waitFor(() => expect(screen.getByTestId("scissors-chart")).toBeInTheDocument());
      expect(screen.queryByTestId("veil-locked")).not.toBeInTheDocument();
    });

    it("the study CTA navigates to the routed Doctrine page (T3-5 retired the takeover)", async () => {
      mockEconomy({
        veil: {
          tier: 0,
          next_unlock_node_id: "class_consciousness",
          next_unlock_label: "Class Consciousness",
          value_produced: null,
          exploitation_rate: null,
        },
      });
      renderCircuitPage();
      await waitFor(() =>
        expect(screen.getByTestId("veil-study-link-exploitation")).toBeInTheDocument(),
      );

      await userEvent.click(screen.getByTestId("veil-study-link-exploitation"));

      expect(screen.getByTestId("stub-doctrine")).toBeInTheDocument();
      expect(useStore.getState().ui.takeover.active).toBeNull();
    });
  });
});
