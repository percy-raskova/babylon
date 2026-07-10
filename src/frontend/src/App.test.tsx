/**
 * Root routing tests (spec-110 B3 stage 2) — the auth gate. The five-region
 * shell smoke test moved to `components/shell/AppShell.test.tsx`; this
 * file only exercises /login <-> /lobby <-> /game/:id redirection.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import App from "./App";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function renderAt(path: string): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App routing", () => {
  it("redirects an unauthenticated visitor to /login", async () => {
    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.json({ status: "ok", data: { is_authenticated: false } }),
      ),
    );
    renderAt("/lobby");
    await waitFor(() => expect(screen.getByPlaceholderText("Username")).toBeInTheDocument());
  });

  it("shows a loading state while the auth check is in flight", () => {
    renderAt("/lobby");
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders the lobby for an authenticated visitor", async () => {
    renderAt("/lobby");
    await waitFor(() => expect(screen.getByText(/Your Games/)).toBeInTheDocument());
  });

  it("renders the cockpit shell at /game/:id for an authenticated visitor", async () => {
    renderAt(`/game/${DEFAULT_GAME_ID}`);
    await waitFor(() => expect(screen.getByTestId("region-statusbar")).toBeInTheDocument());
    expect(useStore.getState().session.activeGameId).toBe(DEFAULT_GAME_ID);
  });

  it("redirects an unknown path to the lobby when authenticated", async () => {
    renderAt("/something-unknown");
    await waitFor(() => expect(screen.getByText(/Your Games/)).toBeInTheDocument());
  });
});
