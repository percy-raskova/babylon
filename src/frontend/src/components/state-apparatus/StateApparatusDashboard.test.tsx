import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { StateApparatusDashboard } from "./StateApparatusDashboard";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeStateApparatusDashboard, makeOrg, makeEvent } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("StateApparatusDashboard", () => {
  it("renders the dashboard once real /state-apparatus/ data loads", async () => {
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("state-apparatus-dashboard")).toBeInTheDocument(),
    );
  });

  it("shows a loud error on a failed fetch", async () => {
    server.use(
      http.get("/api/games/:id/state-apparatus/", () =>
        HttpResponse.json(
          { status: "error", message: "State apparatus unavailable" },
          { status: 500 },
        ),
      ),
    );
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("State apparatus unavailable"),
    );
  });

  it("mounts and unmounts the stateApparatus panel", async () => {
    const { unmount } = render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.stateApparatus.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.stateApparatus.mounted).toBe(false);
  });

  it("renders the repression budget / total heat / org count stat chips", async () => {
    server.use(
      http.get("/api/games/:id/state-apparatus/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeStateApparatusDashboard({
            total_repression_budget: 42.5,
            total_heat: 3.25,
            org_count: 1,
          }),
        }),
      ),
    );
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("state-apparatus-stat-chips")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("stat-repression budget")).toHaveTextContent("42.5");
    expect(screen.getByTestId("stat-total heat")).toHaveTextContent("3.25");
    expect(screen.getByTestId("stat-org count")).toHaveTextContent("1");
  });

  it("renders the seeded state-apparatus org (id/name/budget/heat)", async () => {
    server.use(
      http.get("/api/games/:id/state-apparatus/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeStateApparatusDashboard({
            organizations: [
              makeOrg({
                id: "ORG002",
                name: "Detroit Police Department",
                org_type: "state_apparatus",
                budget: 40,
                heat: 0.1,
                vanguard: null,
              }),
            ],
            org_count: 1,
          }),
        }),
      ),
    );
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("state-apparatus-orgs")).toBeInTheDocument());
    const row = screen.getByTestId("state-org-ORG002");
    expect(row).toHaveTextContent("Detroit Police Department");
    expect(row).toHaveTextContent("ORG002");
    expect(row).toHaveTextContent("40.0");
    expect(row).toHaveTextContent("0.10");
  });

  it("shows an honest empty state when no state-apparatus orgs are seeded", async () => {
    server.use(
      http.get("/api/games/:id/state-apparatus/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeStateApparatusDashboard({ organizations: [], org_count: 0 }),
        }),
      ),
    );
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("state-apparatus-orgs-empty")).toBeInTheDocument(),
    );
  });

  it("renders recent_actions in the repression-action feed", async () => {
    server.use(
      http.get("/api/games/:id/state-apparatus/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeStateApparatusDashboard({
            recent_actions: [
              makeEvent({
                id: "action-1",
                type: "state_surveillance",
                tick: 3,
                severity: "informational",
                title: "State Surveillance",
              }),
              makeEvent({
                id: "action-2",
                type: "state_repression",
                tick: 4,
                severity: "warning",
                title: "State Repression",
              }),
            ],
          }),
        }),
      ),
    );
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("state-actions-feed")).toBeInTheDocument());
    expect(screen.getByTestId("state-action-action-1")).toHaveTextContent("State Surveillance");
    expect(screen.getByTestId("state-action-action-2")).toHaveTextContent("State Repression");
  });

  it("shows an honest empty state when no state actions have fired yet", async () => {
    server.use(
      http.get("/api/games/:id/state-apparatus/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeStateApparatusDashboard({ recent_actions: [] }),
        }),
      ),
    );
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("state-actions-empty")).toBeInTheDocument());
    expect(screen.getByTestId("state-actions-empty")).toHaveTextContent(
      "No state actions this session yet.",
    );
  });

  it("shows an honest empty note when state_finances is {} (no scenario seeds it yet)", async () => {
    server.use(
      http.get("/api/games/:id/state-apparatus/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeStateApparatusDashboard({ state_finances: {} }),
        }),
      ),
    );
    render(<StateApparatusDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("state-finances-empty")).toBeInTheDocument());
  });
});
