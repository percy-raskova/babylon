import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
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

describe("EconomyDashboard", () => {
  it("renders the dashboard once real /economy/ data loads", async () => {
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("economy-dashboard")).toBeInTheDocument());
  });

  it("shows a loud empty state when has_data is false", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEconomyDashboardPayload({ has_data: false }),
        }),
      ),
    );
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("economy-no-data")).toBeInTheDocument());
  });

  it("shows a loud error on a failed fetch", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({ status: "error", message: "Economy unavailable" }, { status: 500 }),
      ),
    );
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Economy unavailable"));
  });

  it("mounts and unmounts the economy panel", async () => {
    const { unmount } = render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.economy.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.economy.mounted).toBe(false);
  });

  it("no longer renders the wealth-by-class-role composition (T2-7: relocated to CircuitPage)", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEconomyDashboardPayload({
            wealth_by_class_role: { periphery_proletariat: 40, core_bourgeoisie: 60 },
          }),
        }),
      ),
    );
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
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
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("crisis-timeline")).toBeInTheDocument());
    const rows = screen.getAllByTestId(/^crisis-row-/);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("T2");
    expect(rows[1]).toHaveTextContent("T5");
  });

  it("shows an honest empty state when the journal has no crisis events", async () => {
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("crisis-timeline-empty")).toBeInTheDocument());
  });

  it("renders every chip live from a fully-populated payload — no phantoms (spec-116 4d.6)", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEconomyDashboardPayload({ profit_rate: 0.153, occ: 2.4 }),
        }),
      ),
    );
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("economy-stat-chips")).toBeInTheDocument());

    expect(screen.getByTestId("stat-profit rate")).toHaveTextContent("0.153");
    expect(screen.getByTestId("stat-occ")).toHaveTextContent("2.40");
    // With a full payload, no chip in the row may fall back to "no data" —
    // that would be a phantom (a TS-declared field the backend never sent).
    expect(screen.getByTestId("economy-stat-chips")).not.toHaveTextContent("no data");
  });

  it("keeps honest 'no data' on exactly the year-boundary chips pre-boundary (spec-116 4d.6)", async () => {
    // Default fixture: profit_rate/occ null (pre-tick-52 cadence honesty).
    render(<EconomyDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("economy-stat-chips")).toBeInTheDocument());

    expect(screen.getByTestId("stat-profit rate")).toHaveTextContent("no data");
    expect(screen.getByTestId("stat-occ")).toHaveTextContent("no data");
    // Every other chip stays live — tick-26 "all dead" can never recur.
    expect(screen.getByTestId("stat-value produced")).not.toHaveTextContent("no data");
    expect(screen.getByTestId("stat-rent pool")).not.toHaveTextContent("no data");
    expect(screen.getByTestId("stat-wage flow")).not.toHaveTextContent("no data");
  });
});
