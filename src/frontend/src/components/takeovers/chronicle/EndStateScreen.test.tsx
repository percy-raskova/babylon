/**
 * EndStateScreen — six distinct epilogues (spec-116 FR-116-4.2).
 *
 * The six-row table mirrors the backend SoT (web/game/epilogues.py): real
 * headlines + palettes, synthetic bodies. The component under test is pure
 * pass-through — distinctness itself is pinned backend-side in
 * tests/unit/web/test_epilogues.py; this file pins the 6-way rendering:
 * per-outcome headline/body/palette class/data-outcome, accepted-at-tick
 * framing, and the honest pending state.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { EndStateScreen } from "./EndStateScreen";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeEndgameState } from "@/test/fixtures";
import type { EndgameState } from "@/types/dialectic";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function mockEndgame(overrides: Partial<EndgameState>): void {
  server.use(
    http.get("/api/games/:id/endgame/", () =>
      HttpResponse.json({ status: "ok", data: makeEndgameState(overrides) }),
    ),
  );
}

const SIX_OUTCOMES = [
  { outcome: "revolutionary_victory", palette: "rupture", headline: "BABYLON FALLS" },
  { outcome: "ecological_collapse", palette: "defeat", headline: "THE EARTH BETRAYED" },
  { outcome: "fascist_consolidation", palette: "defeat", headline: "ORDER IS RESTORED" },
  { outcome: "red_ogv", palette: "defeat", headline: "RED FLAGS OVER EMPIRE" },
  { outcome: "fragmented_collapse", palette: "defeat", headline: "THE MAP SHATTERS" },
  { outcome: "unresolved", palette: "unresolved", headline: "THE STRUGGLE CONTINUES" },
] as const;

describe("EndStateScreen — six distinct epilogues (spec-116 FR-116-4.2)", () => {
  it.each(SIX_OUTCOMES)(
    "renders $outcome with its own headline, body, and $palette palette",
    async ({ outcome, palette, headline }) => {
      mockEndgame({
        outcome,
        headline,
        epilogue: `${outcome} epilogue body.`,
        palette,
        tick: 5200,
        stats: { final_tick: 5200, consciousness: 0.42, solidarity_edges: 3, heat: 0.31 },
      });
      render(<EndStateScreen gameId={DEFAULT_GAME_ID} />);
      await waitFor(() => expect(screen.getByText(headline)).toBeInTheDocument());
      expect(screen.getByText(`${outcome} epilogue body.`)).toBeInTheDocument();
      const root = screen.getByTestId("end-state");
      expect(root).toHaveClass(`end-state--${palette}`);
      expect(root).toHaveAttribute("data-outcome", outcome);
    },
  );

  it("renders the accepted-at-tick framing for a player-accepted outcome", async () => {
    mockEndgame({
      outcome: "fascist_consolidation",
      headline: "ORDER IS RESTORED",
      epilogue: "The fash take hold.",
      palette: "defeat",
      accepted_at_tick: 3120,
    });
    render(<EndStateScreen gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("end-state-accepted")).toHaveTextContent(/accepted at tick 3120/i),
    );
  });

  it("omits the accepted framing for a horizon-terminated outcome", async () => {
    mockEndgame({
      outcome: "unresolved",
      headline: "THE STRUGGLE CONTINUES",
      epilogue: "One hundred years, and no verdict.",
      palette: "unresolved",
      accepted_at_tick: null,
    });
    render(<EndStateScreen gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByText("THE STRUGGLE CONTINUES")).toBeInTheDocument());
    expect(screen.queryByTestId("end-state-accepted")).not.toBeInTheDocument();
  });

  it("does not render the degraded machine summary once an epilogue exists", async () => {
    mockEndgame({
      outcome: "red_ogv",
      headline: "RED FLAGS OVER EMPIRE",
      summary: "Endgame Reached",
      epilogue: "The settler bargain was rebranded.",
      palette: "defeat",
    });
    render(<EndStateScreen gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByText("The settler bargain was rebranded.")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Endgame Reached")).not.toBeInTheDocument();
  });

  it("keeps the honest pending state while the game is in progress", async () => {
    // Default fixture: outcome null (Constitution III.11 — never fabricate).
    render(<EndStateScreen gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(
        screen.getByText("Operation in progress — no terminal outcome yet."),
      ).toBeInTheDocument(),
    );
    const root = screen.getByTestId("end-state");
    expect(root).toHaveClass("end-state--pending");
    expect(root).toHaveAttribute("data-outcome", "pending");
  });
});
