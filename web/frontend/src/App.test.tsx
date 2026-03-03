/**
 * Unit tests for the root App component.
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";

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
    render(<App />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows login page when not authenticated", async () => {
    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.json({
          status: "ok",
          data: { is_authenticated: false, username: null },
        }),
      ),
    );
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("BABYLON")).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
  });

  it("shows game list when authenticated", async () => {
    server.use(
      http.get("/accounts/whoami/", () =>
        HttpResponse.json({
          status: "ok",
          data: { is_authenticated: true, username: "alice" },
        }),
      ),
      http.get("/api/games/", () => HttpResponse.json({ status: "ok", data: [] })),
    );
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Your Games")).toBeInTheDocument();
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

    render(<App />);

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
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("Username"), "bob");
    await user.type(screen.getByPlaceholderText("Password"), "secret");
    await user.click(screen.getByText("Log In"));

    await waitFor(() => {
      expect(screen.getByText("Your Games")).toBeInTheDocument();
    });
  });
});
