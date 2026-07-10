import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { InspectorPanel } from "./InspectorPanel";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
  useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);
});

describe("InspectorPanel", () => {
  it("shows a loud empty state when nothing is selected", () => {
    render(<InspectorPanel />);
    expect(screen.getByTestId("inspector-empty")).toBeInTheDocument();
  });

  it("renders org fields with consciousness null-honesty when the org has no computed distribution", async () => {
    server.use(
      http.get("/api/games/:id/org/:entityId/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            kind: "org",
            id: "org-1",
            class_character: "proletarian",
            budget: 42.5,
            cohesion: 0.6,
            heat: 0.3,
            consciousness: null,
          },
        }),
      ),
    );
    useStore.getState().map.setSelection({ kind: "org", id: "org-1" });
    render(<InspectorPanel />);

    await waitFor(() => expect(screen.getByTestId("inspector-panel")).toBeInTheDocument());
    expect(screen.getByText("proletarian")).toBeInTheDocument();
    expect(screen.getByTestId("consciousness-no-data")).toBeInTheDocument();
  });

  it("renders the real consciousness breakdown when present", async () => {
    server.use(
      http.get("/api/games/:id/org/:entityId/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            kind: "org",
            id: "org-1",
            consciousness: { liberal: 0.1, fascist: 0.05, revolutionary: 0.85 },
          },
        }),
      ),
    );
    useStore.getState().map.setSelection({ kind: "org", id: "org-1" });
    render(<InspectorPanel />);

    await waitFor(() => expect(screen.getByTestId("consciousness-breakdown")).toBeInTheDocument());
    expect(screen.getByText("0.850")).toBeInTheDocument();
  });

  it("renders territory fields including habitability", async () => {
    server.use(
      http.get("/api/games/:id/hex/:entityId/", () =>
        HttpResponse.json({
          status: "ok",
          data: { kind: "hex", id: "territory-1", habitability: 0.62, biocapacity: 0.3, heat: 0.4 },
        }),
      ),
    );
    useStore.getState().map.setSelection({ kind: "hex", id: "territory-1" });
    render(<InspectorPanel />);

    await waitFor(() => expect(screen.getByTestId("inspector-panel")).toBeInTheDocument());
    expect(screen.getByText("0.62")).toBeInTheDocument();
  });

  it("shows a loud error on a failed inspector fetch", async () => {
    server.use(
      http.get("/api/games/:id/node/:entityId/", () =>
        HttpResponse.json({ status: "error", message: "Node not found" }, { status: 404 }),
      ),
    );
    useStore.getState().map.setSelection({ kind: "node", id: "unknown" });
    render(<InspectorPanel />);

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Node not found"));
  });
});
