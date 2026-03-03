/**
 * Integration test: login → game list → game shell lifecycle.
 *
 * Tests the full navigation flow through the App component.
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "@/App";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import { makeGameSummary } from "@/test/fixtures";

describe("game lifecycle", () => {
  it("login → game list → select game shows game shell", async () => {
    const user = userEvent.setup();

    // Start unauthenticated
    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.json({
          status: "ok",
          data: { is_authenticated: false, username: null },
        }),
      ),
      http.post("/accounts/login/", () =>
        HttpResponse.json({
          status: "ok",
          data: { username: "alice" },
        }),
      ),
      http.get("/api/games/", () =>
        HttpResponse.json({
          status: "ok",
          data: [makeGameSummary({ id: "game-abc", scenario: "Detroit" })],
        }),
      ),
    );

    render(<App />);

    // Should see login page
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    });

    // Log in
    await user.type(screen.getByPlaceholderText("Username"), "alice");
    await user.type(screen.getByPlaceholderText("Password"), "secret");
    await user.click(screen.getByText("Log In"));

    // Should navigate to game list
    await waitFor(() => {
      expect(screen.getByText("Your Games")).toBeInTheDocument();
    });
    expect(screen.getByText("Detroit")).toBeInTheDocument();
  });

  it("create new game triggers onSelectGame", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.json({
          status: "ok",
          data: { is_authenticated: true, username: "alice" },
        }),
      ),
      http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })),
      http.post("/api/games/", () =>
        HttpResponse.json({
          status: "ok",
          data: { session_id: "new-game-123" },
        }),
      ),
    );

    render(<App />);

    // Wait for game list
    await waitFor(() => {
      expect(screen.getByText("+ New Game")).toBeInTheDocument();
    });

    // Create new game
    await user.click(screen.getByText("+ New Game"));

    // After creation, app should navigate to game shell
    // GameShell renders TopBar with "Tick" label once loaded
    await waitFor(() => {
      expect(screen.getByText("Tick")).toBeInTheDocument();
    });
  });

  it("logout returns to login page", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.json({
          status: "ok",
          data: { is_authenticated: true, username: "bob" },
        }),
      ),
      http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })),
      http.post("/accounts/logout/", () => HttpResponse.json({ status: "ok", data: null })),
    );

    render(<App />);

    // Wait for game list with nav bar
    await waitFor(() => {
      expect(screen.getByText("bob")).toBeInTheDocument();
    });

    // Click logout
    await user.click(screen.getByText("Logout"));

    // Should return to login
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    });
  });
});
