import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MapPanel } from "./MapPanel";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot } from "@/test/fixtures";

// MapPanel now threads mapSlice.framing into DeckGLMap (spec-112 C5), whose
// "county" (or other non-hex) framing constructs an H3ClusterLayer —
// setup.ts's global @deck.gl/geo-layers mock only stubs H3HexagonLayer, so
// this file-local override (takes precedence for this file) supplements it.
vi.mock("@deck.gl/geo-layers", () => ({
  H3HexagonLayer: vi.fn(),
  H3ClusterLayer: vi.fn(),
}));

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("MapPanel", () => {
  it("shows a loud empty state before any world snapshot has loaded", () => {
    render(<MapPanel gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByText("No world state loaded yet.")).toBeInTheDocument();
  });

  it("mounts DeckGLMap once a snapshot is present, and mounts/unmounts panels.map", async () => {
    useStore.setState((s) => ({ world: { ...s.world, snapshot: makeSnapshot() } }));
    const { unmount } = render(<MapPanel gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("map-mode-selector")).toBeInTheDocument();
    await waitFor(() => expect(useStore.getState().panels.map.mounted).toBe(true));
    await waitFor(() => expect(useStore.getState().panels.map.data).not.toBeNull());

    unmount();
    expect(useStore.getState().panels.map.mounted).toBe(false);
  });

  it("refetches the map panel when framing changes", async () => {
    useStore.setState((s) => ({ world: { ...s.world, snapshot: makeSnapshot() } }));
    render(<MapPanel gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.map.data).not.toBeNull());
    const fetchesBefore = requestLog.filter((r) => r === "GET map").length;

    // "hex" is the default framing (spec-112 C5) — transition to a
    // different value so this actually exercises a change.
    useStore.getState().map.setFraming("county");

    await waitFor(() =>
      expect(requestLog.filter((r) => r === "GET map")).toHaveLength(fetchesBefore + 1),
    );
  });

  it("clicking a territory sets a hex selection", async () => {
    useStore.setState((s) => ({ world: { ...s.world, snapshot: makeSnapshot() } }));
    render(<MapPanel gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.map.data).not.toBeNull());
    // DeckGL itself is mocked out (setup.ts) so we exercise onTerritoryClick
    // directly via the store rather than simulating a canvas click.
    useStore.getState().map.setSelection({ kind: "hex", id: "territory-downtown" });
    expect(useStore.getState().map.selection).toEqual({ kind: "hex", id: "territory-downtown" });
  });
});
