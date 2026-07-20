import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Routes, Route } from "react-router";
import { server } from "@/test/server";
import { EconomyDashboard } from "./EconomyDashboard";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeEconomyDashboardPayload, makeJournalPayload, makeEvent } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

/** `EconomyDashboard` uses `useNavigate` (G4: the Study CTA) — needs a Router. */
function renderDashboard(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}`]}>
      <Routes>
        <Route path="/game/:id" element={<EconomyDashboard gameId={DEFAULT_GAME_ID} />} />
        <Route
          path="/game/:id/doctrine"
          element={<div data-testid="stub-doctrine">DOCTRINE</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

function mockEconomy(overrides: Parameters<typeof makeEconomyDashboardPayload>[0]): void {
  server.use(
    http.get("/api/games/:id/economy/", () =>
      HttpResponse.json({ status: "ok", data: makeEconomyDashboardPayload(overrides) }),
    ),
  );
}

describe("EconomyDashboard", () => {
  it("renders the dashboard once real /economy/ data loads", async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId("economy-dashboard")).toBeInTheDocument());
  });

  it("shows a loud empty state when has_data is false", async () => {
    mockEconomy({ has_data: false });
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId("economy-no-data")).toBeInTheDocument());
  });

  it("shows a loud error on a failed fetch", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({ status: "error", message: "Economy unavailable" }, { status: 500 }),
      ),
    );
    renderDashboard();
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Economy unavailable"));
  });

  it("mounts and unmounts the economy panel", async () => {
    const { unmount } = renderDashboard();
    await waitFor(() => expect(useStore.getState().panels.economy.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.economy.mounted).toBe(false);
  });

  it("no longer renders the wealth-by-class-role composition (T2-7: relocated to CircuitPage)", async () => {
    mockEconomy({
      wealth_by_class_role: { periphery_proletariat: 40, core_bourgeoisie: 60 },
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId("economy-dashboard")).toBeInTheDocument());
    expect(screen.queryByTestId("breakdown-bar")).not.toBeInTheDocument();
  });

  it("renders crisis-phase-transition rows from the journal, tick-ordered", async () => {
    server.use(
      http.get("/api/games/:id/journal/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeJournalPayload({
            events: [
              makeEvent({
                id: "crisis-2",
                type: "crisis_phase_transition",
                tick: 5,
                severity: "warning",
                title: "Crisis Phase Transition",
              }),
              makeEvent({
                id: "crisis-1",
                type: "crisis_phase_transition",
                tick: 2,
                severity: "warning",
                title: "Crisis Phase Transition",
              }),
              makeEvent({ id: "not-a-crisis", type: "surplus_extraction", tick: 3 }),
            ],
          }),
        }),
      ),
    );
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId("crisis-timeline")).toBeInTheDocument());
    const rows = screen.getAllByTestId(/^crisis-row-/);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("T2");
    expect(rows[1]).toHaveTextContent("T5");
  });

  it("shows an honest empty state when the journal has no crisis events", async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId("crisis-timeline-empty")).toBeInTheDocument());
  });

  it("renders every chip live from a fully-populated payload — no phantoms (spec-116 4d.6)", async () => {
    mockEconomy({ profit_rate: 0.153, occ: 2.4 });
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId("economy-stat-chips")).toBeInTheDocument());

    expect(screen.getByTestId("stat-profit rate")).toHaveTextContent("0.153");
    expect(screen.getByTestId("stat-occ")).toHaveTextContent("2.40");
    // With a full payload, no chip in the row may fall back to "no data" —
    // that would be a phantom (a TS-declared field the backend never sent).
    expect(screen.getByTestId("economy-stat-chips")).not.toHaveTextContent("no data");
  });

  it("keeps honest 'no data' on exactly the year-boundary chips pre-boundary (spec-116 4d.6)", async () => {
    // Default fixture: profit_rate/occ null (pre-tick-52 cadence honesty).
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId("economy-stat-chips")).toBeInTheDocument());

    expect(screen.getByTestId("stat-profit rate")).toHaveTextContent("no data");
    expect(screen.getByTestId("stat-occ")).toHaveTextContent("no data");
    // Every other chip stays live — tick-26 "all dead" can never recur.
    expect(screen.getByTestId("stat-value produced")).not.toHaveTextContent("no data");
    expect(screen.getByTestId("stat-rent pool")).not.toHaveTextContent("no data");
    expect(screen.getByTestId("stat-wage flow")).not.toHaveTextContent("no data");
  });

  describe("the Veil of Money (G4: closes the legacy top-level leak)", () => {
    it("tier 0: locks Value Produced/Exploitation behind a VeilLock naming the real next doctrine node", async () => {
      mockEconomy({
        value_produced: null,
        exploitation_rate: null,
        rent_extracted: null,
        veil: {
          tier: 0,
          next_unlock_node_id: "class_consciousness",
          next_unlock_label: "Class Consciousness",
          value_produced: null,
          exploitation_rate: null,
        },
      });
      renderDashboard();
      await waitFor(() => expect(screen.getByTestId("veil-locked")).toBeInTheDocument());
      expect(screen.queryByTestId("stat-value produced")).not.toBeInTheDocument();
      expect(screen.queryByTestId("stat-exploitation")).not.toBeInTheDocument();
      expect(screen.getByText(/Study: Class Consciousness/)).toBeInTheDocument();
      // No client-side inspection can pierce it — the values are absent,
      // not merely hidden by CSS/JSX (they were never in the DOM at all).
      expect(screen.queryByText("100")).not.toBeInTheDocument();
    });

    it("tier 2 (default fixture, tier >= 1): Value Produced/Exploitation read real numbers off veil.*", async () => {
      renderDashboard();
      await waitFor(() => expect(screen.getByTestId("economy-stat-chips")).toBeInTheDocument());
      expect(screen.queryByTestId("veil-locked")).not.toBeInTheDocument();
      expect(screen.getByTestId("stat-value produced")).toHaveTextContent("100");
      expect(screen.getByTestId("stat-exploitation")).toHaveTextContent("0.200");
    });

    it("the study CTA navigates to the routed Doctrine page", async () => {
      mockEconomy({
        value_produced: null,
        exploitation_rate: null,
        veil: {
          tier: 0,
          next_unlock_node_id: "class_consciousness",
          next_unlock_label: "Class Consciousness",
          value_produced: null,
          exploitation_rate: null,
        },
      });
      renderDashboard();
      await waitFor(() =>
        expect(screen.getByTestId("veil-study-link-economy")).toBeInTheDocument(),
      );
      await userEvent.click(screen.getByTestId("veil-study-link-economy"));
      expect(screen.getByTestId("stub-doctrine")).toBeInTheDocument();
    });
  });
});
