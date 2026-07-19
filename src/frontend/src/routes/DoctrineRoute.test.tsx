import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { DoctrineRoute } from "./DoctrineRoute";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("DoctrineRoute", () => {
  it("resolves :id and renders the DoctrinePage, mounting the relocated DoctrineTakeover canvas", async () => {
    render(
      <MemoryRouter initialEntries={[`/game/${DEFAULT_GAME_ID}/doctrine`]}>
        <Routes>
          <Route path="/game/:id/doctrine" element={<DoctrineRoute />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("region-doctrine")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("doctrine-takeover")).toBeInTheDocument());
  });
});
