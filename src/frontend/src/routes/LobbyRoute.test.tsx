import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { LobbyRoute } from "./LobbyRoute";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState } from "@/test/handlers";
import { makeGameSummary } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function renderLobby(): void {
  render(
    <MemoryRouter initialEntries={["/lobby"]}>
      <Routes>
        <Route path="/lobby" element={<LobbyRoute />} />
        <Route path="/game/:id" element={<div>GAME SHELL</div>} />
        <Route path="/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LobbyRoute", () => {
  it("lists real games by codename and navigates on click", async () => {
    renderLobby();
    await waitFor(() => expect(screen.getByText("CRIMSON HARVEST")).toBeInTheDocument());
    await userEvent.click(screen.getByText("CRIMSON HARVEST"));
    expect(screen.getByText("GAME SHELL")).toBeInTheDocument();
  });

  it("renders scenario, tick, status, and date on each row", async () => {
    renderLobby();
    await waitFor(() => expect(screen.getByText("CRIMSON HARVEST")).toBeInTheDocument());
    // makeGameSummary: scenario "default" (no catalog name -> raw key fallback),
    // tick 5, active, created 2026-03-01T12:00:00Z -> ISO date prefix.
    expect(screen.getByText("default · Tick 5 · ACTIVE · 2026-03-01")).toBeInTheDocument();
  });

  it("creates a new game via the real /api/games/ POST and navigates to it", async () => {
    renderLobby();
    await waitFor(() => expect(screen.getByText("Wayne County Organizer")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /new game/i }));
    await waitFor(() => expect(screen.getByText("GAME SHELL")).toBeInTheDocument());
  });

  it("create sends the selected curated difficulty preset and a rolled rng_seed", async () => {
    let createBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/games/", async ({ request }) => {
        createBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          { status: "ok", data: { session_id: "game-001" } },
          { status: 201 },
        );
      }),
    );
    renderLobby();
    await waitFor(() =>
      expect(screen.getByTestId("difficulty-option-besieged")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("difficulty-option-besieged"));
    await userEvent.click(screen.getByRole("button", { name: /new game/i }));

    await waitFor(() => expect(createBody).not.toBeNull());
    // TS narrows `createBody` (a `let` reassigned only inside the nested MSW
    // handler closure) down to its initial `null` at this point — the
    // checker doesn't track cross-closure mutation. Re-widen explicitly;
    // behavior is unchanged (still the same optional-chained reads).
    const body = createBody as Record<string, unknown> | null;
    expect(body?.defines).toEqual({
      economy: { extraction_efficiency: 0.9 },
      survival: { default_subsistence: 0.4 },
    });
    expect(typeof body?.rng_seed).toBe("number");
  });

  it("delete is arm-then-confirm: two clicks issue the DELETE and drop the row", async () => {
    let deleted = false;
    server.use(
      http.delete("/api/games/:id/", () => {
        deleted = true;
        return HttpResponse.json({ status: "ok", data: { deleted: true } });
      }),
      http.get("/api/games/", () =>
        HttpResponse.json({ status: "ok", data: deleted ? [] : [makeGameSummary()] }),
      ),
    );
    renderLobby();
    await waitFor(() => expect(screen.getByTestId("game-delete-game-001")).toBeInTheDocument());

    await userEvent.click(screen.getByTestId("game-delete-game-001"));
    expect(deleted).toBe(false); // first click only arms the button
    await userEvent.click(screen.getByTestId("game-delete-game-001"));

    await waitFor(() =>
      expect(screen.queryByTestId("game-option-game-001")).not.toBeInTheDocument(),
    );
    expect(deleted).toBe(true);
    expect(screen.queryByText("GAME SHELL")).not.toBeInTheDocument(); // no row navigation
  });

  it("archive issues POST /archive/ without navigating and re-lists as abandoned", async () => {
    let archived = false;
    server.use(
      http.post("/api/games/:id/archive/", () => {
        archived = true;
        return HttpResponse.json({ status: "ok", data: { status: "abandoned" } });
      }),
      http.get("/api/games/", () =>
        HttpResponse.json({
          status: "ok",
          data: [makeGameSummary({ status: archived ? "abandoned" : "active" })],
        }),
      ),
    );
    renderLobby();
    await waitFor(() => expect(screen.getByTestId("game-archive-game-001")).toBeInTheDocument());

    await userEvent.click(screen.getByTestId("game-archive-game-001"));

    await waitFor(() =>
      expect(screen.getByText("default · Tick 5 · ABANDONED · 2026-03-01")).toBeInTheDocument(),
    );
    expect(screen.queryByText("GAME SHELL")).not.toBeInTheDocument();
    // An archived row offers no second archive affordance.
    expect(screen.queryByTestId("game-archive-game-001")).not.toBeInTheDocument();
  });

  it("logs out and returns to /login", async () => {
    renderLobby();
    await waitFor(() => expect(screen.getByText("CRIMSON HARVEST")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /logout/i }));
    await waitFor(() => expect(screen.getByText("LOGIN")).toBeInTheDocument());
  });
});
