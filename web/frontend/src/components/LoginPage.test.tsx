/**
 * Unit tests for the LoginPage component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from "./LoginPage";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";

describe("LoginPage", () => {
  it("renders login form", () => {
    render(<LoginPage onLogin={vi.fn()} />);
    expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByText("Log In")).toBeInTheDocument();
  });

  it("renders title", () => {
    render(<LoginPage onLogin={vi.fn()} />);
    expect(screen.getByText("BABYLON")).toBeInTheDocument();
    expect(screen.getByText("The Fall of America")).toBeInTheDocument();
  });

  it("submits credentials and calls onLogin on success", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    render(<LoginPage onLogin={onLogin} />);

    await user.type(screen.getByPlaceholderText("Username"), "testuser");
    await user.type(screen.getByPlaceholderText("Password"), "secret");
    await user.click(screen.getByText("Log In"));

    await waitFor(() => {
      expect(onLogin).toHaveBeenCalledWith({
        is_authenticated: true,
        username: "testuser",
      });
    });
  });

  it("shows error on failed login", async () => {
    server.use(
      http.post("/accounts/login/", () =>
        HttpResponse.json({
          status: "error",
          data: null,
          message: "Invalid credentials",
        }),
      ),
    );

    const user = userEvent.setup();
    render(<LoginPage onLogin={vi.fn()} />);

    await user.type(screen.getByPlaceholderText("Username"), "wrong");
    await user.type(screen.getByPlaceholderText("Password"), "wrong");
    await user.click(screen.getByText("Log In"));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("shows submitting state", async () => {
    // Use a delayed response to test the submitting state
    server.use(
      http.post("/accounts/login/", async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json({
          status: "ok",
          data: { username: "testuser" },
        });
      }),
    );

    const user = userEvent.setup();
    render(<LoginPage onLogin={vi.fn()} />);

    await user.type(screen.getByPlaceholderText("Username"), "test");
    await user.type(screen.getByPlaceholderText("Password"), "pass");
    await user.click(screen.getByText("Log In"));

    // Button should show "Logging in..." briefly
    expect(screen.getByText("Logging in...")).toBeInTheDocument();
  });
});
