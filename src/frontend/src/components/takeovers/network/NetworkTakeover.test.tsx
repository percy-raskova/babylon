/**
 * NetworkTakeover tests (AW4-R2) — fetch-on-open gating, honest empty
 * state, the percolation HUD chip's null/value states, and the honest
 * legend (only real node types / edge modes render a swatch). Sigma is
 * globally mocked in `test/setup.ts`, so these assert on real DOM/store
 * behavior, not canvas pixels.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { NetworkTakeover } from "./NetworkTakeover";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import {
  makeOrgNetworkPayload,
  makeOrgNetworkNode,
  makeOrgNetworkEdge,
  makeOrgNetworkCentrality,
} from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("NetworkTakeover", () => {
  it("fetches the org-network panel on mount and marks it mounted", async () => {
    render(<NetworkTakeover gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.network.mounted).toBe(true));
    await waitFor(() => expect(useStore.getState().panels.network.data).not.toBeNull());
  });

  it("unmounts the panel on unmount (fetch-gating symmetry)", async () => {
    const { unmount } = render(<NetworkTakeover gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.network.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.network.mounted).toBe(false);
  });

  it("renders an honest empty state for an honestly empty network (no fabricated nodes)", async () => {
    render(<NetworkTakeover gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("network-empty")).toBeInTheDocument());
    expect(screen.queryByTestId("network-graph-canvas")).not.toBeInTheDocument();
  });

  it("renders the sigma canvas once real nodes arrive", async () => {
    server.use(
      http.get("/api/games/:id/orgs/network/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeOrgNetworkPayload({
            nodes: [
              makeOrgNetworkNode({ id: "org-1", type: "organization" }),
              makeOrgNetworkNode({ id: "terr-1", type: "territory" }),
            ],
            edges: [makeOrgNetworkEdge({ source: "org-1", target: "terr-1", mode: "presence" })],
            centrality: {
              "org-1": makeOrgNetworkCentrality(),
              "terr-1": makeOrgNetworkCentrality(),
            },
          }),
        }),
      ),
    );

    render(<NetworkTakeover gameId={DEFAULT_GAME_ID} />);

    await waitFor(() => expect(screen.getByTestId("network-graph-canvas")).toBeInTheDocument());
    expect(screen.queryByTestId("network-empty")).not.toBeInTheDocument();
  });

  it("shows the honest '—' percolation chip when percolation_ratio is null", async () => {
    render(<NetworkTakeover gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("stat-percolation")).toBeInTheDocument());
    expect(screen.getByTestId("stat-percolation")).toHaveTextContent("—");
  });

  it("shows the real percolation_ratio value when present", async () => {
    server.use(
      http.get("/api/games/:id/orgs/network/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeOrgNetworkPayload({ percolation_ratio: 0.4231 }),
        }),
      ),
    );

    render(<NetworkTakeover gameId={DEFAULT_GAME_ID} />);

    await waitFor(() => expect(screen.getByTestId("stat-percolation")).toHaveTextContent("0.423"));
  });

  it("renders a legend swatch only for node types / edge modes actually present", async () => {
    server.use(
      http.get("/api/games/:id/orgs/network/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeOrgNetworkPayload({
            nodes: [
              makeOrgNetworkNode({ id: "org-1", type: "organization" }),
              makeOrgNetworkNode({ id: "org-2", type: "organization" }),
            ],
            edges: [makeOrgNetworkEdge({ source: "org-1", target: "org-2", mode: "solidarity" })],
            centrality: {
              "org-1": makeOrgNetworkCentrality(),
              "org-2": makeOrgNetworkCentrality(),
            },
          }),
        }),
      ),
    );

    render(<NetworkTakeover gameId={DEFAULT_GAME_ID} />);

    const legend = await screen.findByTestId("network-legend");
    expect(legend).toHaveTextContent("organization");
    expect(legend).toHaveTextContent("solidarity");
    // Never fabricate a swatch for a type/mode absent from the real payload.
    expect(legend).not.toHaveTextContent("institution");
    expect(legend).not.toHaveTextContent("territory");
    expect(legend).not.toHaveTextContent("presence");
  });
});
