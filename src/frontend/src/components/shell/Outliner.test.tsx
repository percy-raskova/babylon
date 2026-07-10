import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Outliner } from "./Outliner";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import { makeSnapshot, makeOrg, makeCommunitiesDashboardPayload } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("Outliner", () => {
  it("renders a loud empty state for each section before data loads", async () => {
    render(<Outliner gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByText("No organizations in this session.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("No communities formed yet.")).toBeInTheDocument());
    expect(screen.getByText("No faction data — collapse layer unseeded.")).toBeInTheDocument();
  });

  it("lists orgs from the world snapshot and selects one on click", async () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: makeSnapshot({ organizations: [makeOrg()] }) },
    }));
    render(<Outliner gameId={DEFAULT_GAME_ID} />);

    const row = screen.getByText("Workers Union");
    await userEvent.click(row);

    expect(useStore.getState().map.selection).toEqual({ kind: "org", id: "org-workers-union" });
  });

  it("lists communities from the panel", async () => {
    server.use(
      http.get("/api/games/:id/communities/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeCommunitiesDashboardPayload(),
        }),
      ),
    );
    render(<Outliner gameId={DEFAULT_GAME_ID} />);

    await waitFor(() => expect(screen.getByText("proletariat")).toBeInTheDocument());
    await userEvent.click(screen.getByText("proletariat"));
    expect(useStore.getState().map.selection).toEqual({ kind: "community", id: "comm-1" });
  });

  it("lists factions from panels.map's balkanization block and toggles the faction filter", async () => {
    server.use(
      http.get("/api/games/:id/map/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            type: "FeatureCollection",
            features: [],
            metadata: {
              balkanization: {
                factions: [{ id: "FAC_DECOLONIAL", colonial_stance: "abolish" }],
                sovereigns: [],
                territory_influence: [],
              },
            },
          },
        }),
      ),
    );
    // MapPanel owns the mount/fetch of panels.map in the real shell — this
    // test exercises Outliner in isolation, so seed the panel directly.
    await useStore.getState().panels.map.fetch(DEFAULT_GAME_ID);

    render(<Outliner gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByText("FAC_DECOLONIAL")).toBeInTheDocument();

    await userEvent.click(screen.getByText("FAC_DECOLONIAL"));
    expect(useStore.getState().map.factionFilter).toBe("FAC_DECOLONIAL");
    expect(useStore.getState().map.lens).toEqual({ kind: "faction" });

    await userEvent.click(screen.getByText("FAC_DECOLONIAL"));
    expect(useStore.getState().map.factionFilter).toBeNull();
  });

  it("mounts and unmounts the communities panel", async () => {
    const { unmount } = render(<Outliner gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.communities.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.communities.mounted).toBe(false);
  });
});
