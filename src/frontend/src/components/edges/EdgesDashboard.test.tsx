import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { EdgesDashboard } from "./EdgesDashboard";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeEdgesDashboard, makeEdgeRow } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("EdgesDashboard", () => {
  it("renders the dashboard once real /edges/ data loads", async () => {
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("edges-dashboard")).toBeInTheDocument());
  });

  it("shows a loud error on a failed fetch", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({ status: "error", message: "Edges unavailable" }, { status: 500 }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Edges unavailable"));
  });

  it("mounts and unmounts the edges panel", async () => {
    const { unmount } = render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.edges.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.edges.mounted).toBe(false);
  });

  it("renders the total edges / solidarity edges / avg solidarity strength stat chips", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEdgesDashboard({
            total_edges: 495,
            solidarity_strength_stats: { count: 1, avg: 0.05, min: 0.05, max: 0.05 },
          }),
        }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("edges-stat-chips")).toBeInTheDocument());
    expect(screen.getByTestId("stat-total edges")).toHaveTextContent("495");
    expect(screen.getByTestId("stat-solidarity edges")).toHaveTextContent("1");
    expect(screen.getByTestId("stat-avg solidarity strength")).toHaveTextContent("0.050");
  });

  it("renders counts_by_type as a compact breakdown — the shape of the relations", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEdgesDashboard({
            counts_by_type: { exploitation: 200, wages: 150, solidarity: 50 },
          }),
        }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("edges-type-breakdown")).toBeInTheDocument());
    expect(screen.getByTestId("edges-type-breakdown-exploitation")).toHaveTextContent("200");
    expect(screen.getByTestId("edges-type-breakdown-wages")).toHaveTextContent("150");
    expect(screen.getByTestId("edges-type-breakdown-solidarity")).toHaveTextContent("50");
  });

  it("shows an honest empty note when counts_by_mode is {} (EdgeTransitionSystem hasn't run)", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEdgesDashboard({ counts_by_mode: {} }),
        }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("edges-mode-breakdown-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("edges-mode-breakdown-empty")).toHaveTextContent(
      "Edge modes not yet classified (EdgeTransitionSystem).",
    );
  });

  it("shows an honest empty note when no solidarity edges are seeded", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEdgesDashboard({
            solidarity_strength_stats: { count: 0, avg: null, min: null, max: null },
          }),
        }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("edges-solidarity-empty")).toBeInTheDocument());
    expect(screen.getByTestId("stat-avg solidarity strength")).toHaveTextContent("no data");
  });

  it("renders the top_by_tension ranked list with source→target, edge_type, tension, value_flow", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEdgesDashboard({
            top_by_tension: [
              makeEdgeRow({
                source_id: "CLASS001",
                target_id: "CLASS002",
                edge_type: "exploitation",
                tension: 0.91,
                value_flow: 33.3,
              }),
            ],
          }),
        }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("edges-ranked-tension")).toBeInTheDocument());
    const row = screen.getByTestId("edges-ranked-tension-row-CLASS001-CLASS002");
    expect(row).toHaveTextContent("CLASS001");
    expect(row).toHaveTextContent("CLASS002");
    expect(row).toHaveTextContent("exploitation");
    expect(row).toHaveTextContent("0.91");
    expect(row).toHaveTextContent("33.3");
  });

  it("renders the top_by_value_flow ranked list as its own section", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEdgesDashboard({
            top_by_value_flow: [
              makeEdgeRow({
                source_id: "ORG001",
                target_id: "ORG002",
                edge_type: "tribute",
                tension: 0.1,
                value_flow: 999.9,
              }),
            ],
          }),
        }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("edges-ranked-value-flow")).toBeInTheDocument());
    const row = screen.getByTestId("edges-ranked-value-flow-row-ORG001-ORG002");
    expect(row).toHaveTextContent("ORG001");
    expect(row).toHaveTextContent("ORG002");
    expect(row).toHaveTextContent("tribute");
    expect(row).toHaveTextContent("999.9");
  });

  it("shows honest empty states when the ranked lists are empty", async () => {
    server.use(
      http.get("/api/games/:id/edges/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEdgesDashboard({
            total_edges: 0,
            counts_by_type: {},
            top_by_tension: [],
            top_by_value_flow: [],
          }),
        }),
      ),
    );
    render(<EdgesDashboard gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("edges-ranked-tension-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("edges-ranked-value-flow-empty")).toBeInTheDocument();
    expect(screen.getByTestId("edges-type-breakdown-empty")).toBeInTheDocument();
  });
});
