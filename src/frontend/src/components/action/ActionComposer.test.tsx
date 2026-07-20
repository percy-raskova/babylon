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

  it("renders the flat 9-verb grid all-enabled while eligibility is unresolved (honest-null, spec-116 FR-4.8)", async () => {
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);
    const grid = screen.getByTestId("verb-grid");
    expect(grid.querySelectorAll("button")).toHaveLength(9);
    expect(screen.getByRole("button", { name: /investigate/i })).toBeEnabled();
    // Settle the eligibility fetch (default handler: empty verbs list).
    await waitFor(() => expect(screen.getByRole("button", { name: /educate/i })).toBeEnabled());
    expect(screen.queryByTestId("verb-ineligible-reasons")).not.toBeInTheDocument();
  });

  it("disables an ineligible verb with reason + remedy visible (spec-116 FR-4.8)", async () => {
    server.use(
      http.get("/api/games/:id/actions/eligibility/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: DEFAULT_GAME_ID,
            tick: 1,
            org_id: "org-1",
            verbs: [
              {
                verb: "educate",
                eligible: false,
                reason: "No organized community in your territories yet.",
                remedy:
                  "No action can organize a community yet — political education unlocks the moment an organized class appears where you operate.",
                can_afford: true,
                afford_note: null,
              },
              {
                verb: "mobilize",
                eligible: false,
                reason:
                  "No business or civil-society organization within your territories to mobilize against.",
                remedy:
                  "Expand toward workplaces and civil society (MOVE), or wait for new organizations to emerge.",
                can_afford: true,
                afford_note: null,
              },
              {
                verb: "attack",
                eligible: true,
                reason: null,
                remedy: null,
                can_afford: true,
                afford_note: null,
              },
            ],
          },
        }),
      ),
    );
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);

    const educate = screen.getByRole("button", { name: /educate/i });
    await waitFor(() => expect(educate).toBeDisabled());
    expect(educate).toHaveAttribute(
      "title",
      expect.stringContaining("no eligible targets yet: No organized community"),
    );
    expect(screen.getByRole("button", { name: /mobilize/i })).toBeDisabled();

    // Reason + remedy VISIBLE (not tooltip-only), per FR-116-4.8.
    const reasons = screen.getByTestId("verb-ineligible-reasons");
    expect(reasons).toHaveTextContent(/educate/i);
    expect(reasons).toHaveTextContent("No organized community in your territories yet.");
    expect(reasons).toHaveTextContent(/political education unlocks/);

    // Article V: eligible verbs stay enabled; nothing is ever hidden.
    expect(screen.getByRole("button", { name: /attack/i })).toBeEnabled();
    expect(screen.getByTestId("verb-grid").querySelectorAll("button")).toHaveLength(9);
  });

  it("keeps all verbs enabled when the eligibility fetch fails (honest-null)", async () => {
    server.use(
      http.get("/api/games/:id/actions/eligibility/", () =>
        HttpResponse.json({ status: "error", message: "boom" }, { status: 500 }),
      ),
    );
    seedPlayerOrg();
    render(<ActionComposer gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /educate/i })).toBeEnabled());
    expect(screen.queryByTestId("verb-ineligible-reasons")).not.toBeInTheDocument();
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

    // FR-116-4.3: the cost line is visible before submit. This educate stub
    // returns no cost envelope, so the line carries the preview's AP cost.
    expect(screen.getByTestId("verb-cost")).toHaveTextContent("1 AP");
  });

  describe("investigate preset (Track 1 Task 7)", () => {
    it("selects INVESTIGATE and pre-fills its target when actions.preset is set before mount", async () => {
      seedPlayerOrg();
      useStore.getState().actions.presetInvestigate("territory-99", "Wayne County");

      render(<ActionComposer gameId={DEFAULT_GAME_ID} />);

      // The composer opened directly on the INVESTIGATE form (not the grid
      // requiring a manual click), and the target is visibly pre-filled.
      expect(await screen.findByTestId("preset-target-note")).toHaveTextContent("Wayne County");
      // The preset is consumed exactly once — revisiting the grid must not
      // silently reapply a stale preset to a different verb.
      expect(useStore.getState().actions.preset).toBeNull();
    });

    it("does nothing special when no preset is queued (existing flow unchanged)", () => {
      seedPlayerOrg();
      render(<ActionComposer gameId={DEFAULT_GAME_ID} />);
      expect(screen.queryByTestId("preset-target-note")).not.toBeInTheDocument();
    });

    it("clears the preset target when the user switches verbs (PR #211 review)", async () => {
      seedPlayerOrg();
      useStore.getState().actions.presetInvestigate("territory-99", "Wayne County");

      render(<ActionComposer gameId={DEFAULT_GAME_ID} />);
      expect(await screen.findByTestId("preset-target-note")).toHaveTextContent("Wayne County");

      await userEvent.click(screen.getByRole("button", { name: /educate/i }));

      // The INVESTIGATE preset's target dies with the verb it was queued
      // for — it must not silently pre-target EDUCATE (or any other verb
      // the user switches to).
      expect(screen.queryByTestId("preset-target-note")).not.toBeInTheDocument();
    });
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
