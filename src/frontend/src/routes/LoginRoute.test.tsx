import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { LoginRoute } from "./LoginRoute";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function renderLogin(): void {
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/lobby" element={<div>LOBBY</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginRoute", () => {
  it("navigates to /lobby on a successful login", async () => {
    renderLogin();
    await userEvent.type(screen.getByPlaceholderText("Username"), "percy");
    await userEvent.type(screen.getByPlaceholderText("Password"), "correct-horse");
    await userEvent.click(screen.getByRole("button", { name: /enter/i }));

    await waitFor(() => expect(screen.getByText("LOBBY")).toBeInTheDocument());
  });

  it("shows a loud error and stays on the login screen on failure", async () => {
    server.use(
      http.post("/accounts/login/", () =>
        HttpResponse.json({ status: "error", message: "Invalid credentials" }, { status: 401 }),
      ),
    );
    renderLogin();
    await userEvent.type(screen.getByPlaceholderText("Username"), "percy");
    await userEvent.type(screen.getByPlaceholderText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /enter/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid credentials"));
  });
});
