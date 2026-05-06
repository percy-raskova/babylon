/**
 * Unit tests for the root App component with React Router.
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import App from "./App";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";

/** Render App inside a MemoryRouter at a given URL. */
function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

/** MSW handler: unauthenticated user. */
function mockUnauthenticated() {
  server.use(
    http.get("/accounts/whoami/", () =>
      HttpResponse.json({
        status: "ok",
        data: { is_authenticated: false, username: null },
      }),
    ),
  );
}

/** MSW handler: authenticated user. */
function mockAuthenticated(username = "alice") {
  server.use(
    http.get("/accounts/whoami/", () =>
      HttpResponse.json({
        status: "ok",
        data: { is_authenticated: true, username },
      }),
    ),
    http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })),
  );
}

describe("App", () => {
  it("shows loading state while checking auth", () => {
    server.use(
      http.get("/accounts/whoami/", async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({
          status: "ok",
          data: { is_authenticated: false, username: null },
        });
      }),
    );
    renderAt("/login");
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows login page when not authenticated", async () => {
    mockUnauthenticated();
    renderAt("/login");

    await waitFor(() => {
      expect(screen.getByText("BABYLON")).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
  });

  it("shows game list when authenticated", async () => {
    mockAuthenticated("alice");
    renderAt("/games");

    await waitFor(() => {
      expect(screen.getByText("Your Operations")).toBeInTheDocument();
    });
    expect(screen.getByText("alice")).toBeInTheDocument();
  });

  it("falls back to login page when auth bootstrap fails", async () => {
    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.text("<html>error</html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    renderAt("/login");

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    });
  });

  it("navigates from login to game list on successful login", async () => {
    const user = userEvent.setup();
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
          data: { username: "bob" },
        }),
      ),
      http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })),
    );
    renderAt("/login");

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("Username"), "bob");
    await user.type(screen.getByPlaceholderText("Password"), "secret");
    await user.click(screen.getByText("Enter"));

    await waitFor(() => {
      expect(screen.getByText("Your Operations")).toBeInTheDocument();
    });
  });

  describe("route rendering (T028)", () => {
    it("/login renders login page for unauthenticated user", async () => {
      mockUnauthenticated();
      renderAt("/login");

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
      });
    });

    it("/games redirects to /login when not authenticated", async () => {
      mockUnauthenticated();
      renderAt("/games");

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
      });
    });

    it("/games/:id redirects to /login when not authenticated", async () => {
      mockUnauthenticated();
      renderAt("/games/test-game-123");

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
      });
    });

    it("/games renders game list for authenticated user", async () => {
      mockAuthenticated("carol");
      renderAt("/games");

      await waitFor(() => {
        expect(screen.getByText("Your Operations")).toBeInTheDocument();
      });
      expect(screen.getByText("carol")).toBeInTheDocument();
    });

    it("/games/:id renders game shell for authenticated user", async () => {
      mockAuthenticated("dave");
      server.use(
        http.get("/api/games/game-42/state/", () =>
          HttpResponse.json({
            status: "ok",
            data: {
              tick: 1,
              session_id: "game-42",
              entities: [],
              territories: [],
              organizations: [],
              institutions: [],
              edges: [],
              economy: {},
              events: [],
            },
          }),
        ),
      );
      renderAt("/games/game-42");

      // TopBar displays gameId.slice(0,8) + "..." and "Tick" label
      await waitFor(() => {
        expect(screen.getByText("Tick")).toBeInTheDocument();
      });
      expect(screen.getByText("dave")).toBeInTheDocument();
    });

    it("unknown route redirects based on auth state", async () => {
      mockAuthenticated();
      renderAt("/unknown-path");

      await waitFor(() => {
        expect(screen.getByText("Your Operations")).toBeInTheDocument();
      });
    });
  });
});
