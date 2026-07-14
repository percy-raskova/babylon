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

  it("renders the wealth-by-class-role composition", async () => {
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
    await waitFor(() => expect(screen.getByTestId("breakdown-bar")).toBeInTheDocument());
    expect(screen.getByText("Periphery Proletariat")).toBeInTheDocument();
    expect(screen.getByText("Core Bourgeoisie")).toBeInTheDocument();
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
});
