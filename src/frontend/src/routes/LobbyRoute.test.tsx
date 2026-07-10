import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { LobbyRoute } from "./LobbyRoute";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState } from "@/test/handlers";

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
  it("lists real games from /api/games/ and navigates on click", async () => {
    renderLobby();
    await waitFor(() => expect(screen.getByText("default")).toBeInTheDocument());
    await userEvent.click(screen.getByText("default"));
    expect(screen.getByText("GAME SHELL")).toBeInTheDocument();
  });

  it("creates a new game via the real /api/games/ POST and navigates to it", async () => {
    renderLobby();
    await waitFor(() => expect(screen.getByText("Wayne County Organizer")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /new game/i }));
    await waitFor(() => expect(screen.getByText("GAME SHELL")).toBeInTheDocument());
  });

  it("logs out and returns to /login", async () => {
    renderLobby();
    await waitFor(() => expect(screen.getByText("default")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /logout/i }));
    await waitFor(() => expect(screen.getByText("LOGIN")).toBeInTheDocument());
  });
});
