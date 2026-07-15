import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { ActionComposer } from "./ActionComposer";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot, makeOrg } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function seedPlayerOrg(): void {
  useStore.setState((s) => ({
    world: {
      ...s.world,
      snapshot: makeSnapshot({
        organizations: [
          makeOrg({ id: "org-1", name: "Wayne County Committee", player_controlled: true }),
        ],
      }),
    },
  }));
}

describe("ActionComposer", () => {
  it("shows a loud empty state when there are no player-controlled orgs", () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({ organizations: [makeOrg({ player_controlled: false })] }),
      },
    }));
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);
    expect(
      screen.getByText("No player-controlled organizations this session."),
    ).toBeInTheDocument();
  });

  it("renders the flat 9-verb grid with every verb enabled (AW3-R1: all 9 have real engine handlers)", () => {
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);
    const grid = screen.getByTestId("verb-grid");
    expect(grid.querySelectorAll("button")).toHaveLength(9);
    expect(screen.getByRole("button", { name: /investigate/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /educate/i })).toBeEnabled();
  });

  it("selecting a verb fetches live targets and renders them", async () => {
    server.use(
      http.get("/api/games/:id/actions/educate/targets/", () =>
        HttpResponse.json({
          targets: [
            {
              community_id: "comm-1",
              territory_name: "Downtown",
              category: "labor",
              credibility: 0.5,
            },
          ],
        }),
      ),
    );
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByRole("button", { name: /educate/i }));

    await waitFor(() => expect(screen.getByTestId("target-picker")).toBeInTheDocument());
    expect(screen.getByText(/Downtown/)).toBeInTheDocument();
  });

  it("submits the exact buildPayload body and clears into the pending list", async () => {
    let capturedBody: unknown;
    server.use(
      http.get("/api/games/:id/actions/educate/targets/", () =>
        HttpResponse.json({
          targets: [
            {
              community_id: "comm-1",
              territory_name: "Downtown",
              category: "labor",
              credibility: 0.5,
            },
          ],
        }),
      ),
      http.post("/api/games/:id/actions/educate/", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ status: "ok", data: null });
      }),
    );
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByRole("button", { name: /educate/i }));
    await waitFor(() => expect(screen.getByText(/Downtown/)).toBeInTheDocument());
    await userEvent.click(screen.getByText(/Downtown/));
    await userEvent.click(screen.getByRole("button", { name: /submit educate/i }));

    await waitFor(() => expect(screen.getByTestId("pending-actions")).toBeInTheDocument());
    expect(capturedBody).toEqual({
      org_id: "org-1",
      target_community_id: "comm-1",
      params: {},
    });
    expect(screen.getByText(/educate/)).toBeInTheDocument();
  });

  it("reproduce (targetRequired: false) can submit without selecting a target", async () => {
    server.use(
      http.get("/api/games/:id/actions/reproduce/targets/", () =>
        HttpResponse.json({ targets: [{ target_id: "org-1", name: "Self" }] }),
      ),
    );
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByRole("button", { name: /reproduce/i }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /submit reproduce/i })).toBeEnabled(),
    );
  });

  it("shows the live preview's ▲ Consciousness chip once a target is selected (Program 17 Wave 1 item W1.2)", async () => {
    // The chip now reflects the real POST /actions/preview/ response
    // (estimated_consciousness_delta), not a hardcoded config sign — the
    // fake constant-direction predictedEffect machinery was deleted.
    server.use(
      http.get("/api/games/:id/actions/educate/targets/", () =>
        HttpResponse.json({
          targets: [
            {
              community_id: "comm-1",
              territory_name: "Downtown",
              category: "labor",
              credibility: 0.5,
            },
          ],
        }),
      ),
      http.post("/api/games/:id/actions/preview/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            estimated_consciousness_delta: 0.15,
            estimated_heat_delta: 0,
            action_point_cost: 1,
            success_probability: 0.8,
            affected_territory_ids: ["comm-1"],
            warnings: [],
          },
        }),
      ),
    );
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByRole("button", { name: /educate/i }));
    await waitFor(() => expect(screen.getByText(/Downtown/)).toBeInTheDocument());
    await userEvent.click(screen.getByText(/Downtown/));

    expect(screen.getByRole("button", { name: /submit educate/i })).toBeEnabled();
    const delta = await screen.findByTestId("predicted-delta");
    expect(delta).toHaveTextContent("▲ Consciousness");
  });

  it("shows a loud submit error when the backend rejects the action", async () => {
    server.use(
      http.get("/api/games/:id/actions/educate/targets/", () =>
        HttpResponse.json({
          targets: [
            {
              community_id: "comm-1",
              territory_name: "Downtown",
              category: "labor",
              credibility: 0.5,
            },
          ],
        }),
      ),
      http.post("/api/games/:id/actions/educate/", () =>
        HttpResponse.json(
          { status: "error", message: "Insufficient cadre labor" },
          { status: 400 },
        ),
      ),
    );
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByRole("button", { name: /educate/i }));
    await waitFor(() => expect(screen.getByText(/Downtown/)).toBeInTheDocument());
    await userEvent.click(screen.getByText(/Downtown/));
    await userEvent.click(screen.getByRole("button", { name: /submit educate/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Insufficient cadre labor"),
    );
    expect(screen.queryByTestId("pending-actions")).not.toBeInTheDocument();
  });
});
