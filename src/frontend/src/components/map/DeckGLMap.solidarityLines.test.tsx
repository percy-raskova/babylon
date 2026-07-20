/**
 * DeckGLMap — the solidarity-line map layer's data wiring (Track 1 / Task
 * 6). Covers what `solidarityLines.test.ts` can't: `mapData.metadata.
 * solidarity_edges` (already present on the same `/map/` response
 * `balkanization` reads — see `types/game.ts`'s `MapSnapshotMetadata`
 * docstring) reaches `buildSolidarityLineLayers` unmodified, honest-empty
 * (no layer, no crash) when the metadata block is empty/absent, and the
 * layer survives under the frozen `region-map` testid via the real
 * `MapStage` -> `DeckGLMap` mount (`MapStage.tsx` owns `data-testid=
 * "region-map"`; `DeckGLMap.tsx` itself does not).
 *
 * deck.gl mocked globally in setup.ts — `LineLayer`/`ScatterplotLayer` are
 * plain `vi.fn()` stubs, so a layer's constructor args are read off
 * `.mock.calls` (mirrors `DeckGLMap.fieldFlow.test.tsx`'s idiom).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { LineLayer, ScatterplotLayer } from "@deck.gl/layers";
import { server } from "@/test/server";
import { DeckGLMap } from "./DeckGLMap";
import { MapStage } from "@/components/shell/MapStage";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot, makeTerritory, makeSolidarityEdgeLine } from "@/test/fixtures";

/** Every constructor-call props object for a mocked deck.gl layer class whose `id` matches. */
function layerCallsById(
  mockedClass: { mock: { calls: unknown[][] } },
  id: string,
): Record<string, unknown>[] {
  return mockedClass.mock.calls
    .map((call) => call[0] as Record<string, unknown>)
    .filter((props) => props.id === id);
}

beforeEach(() => {
  resetStore();
  resetMockGameState();
  vi.mocked(LineLayer).mockClear();
  vi.mocked(ScatterplotLayer).mockClear();
});

describe("DeckGLMap — solidarity-line honest empty / real data rendering", () => {
  it("honest-empty: no solidarity-line layer when mapData carries no solidarity_edges (no visible allies yet)", () => {
    const snapshot = makeSnapshot();
    render(<DeckGLMap snapshot={snapshot} mapData={null} lens={{ kind: "heat" }} />);
    expect(layerCallsById(vi.mocked(LineLayer), "solidarity-lines")).toHaveLength(0);
    expect(
      layerCallsById(vi.mocked(ScatterplotLayer), "solidarity-lines-same-territory"),
    ).toHaveLength(0);
  });

  it("honest-empty: an explicitly empty solidarity_edges array renders no layer either", () => {
    const snapshot = makeSnapshot();
    const mapData = {
      type: "FeatureCollection" as const,
      features: [],
      metadata: { solidarity_edges: [] },
    };
    render(<DeckGLMap snapshot={snapshot} mapData={mapData} lens={{ kind: "heat" }} />);
    expect(layerCallsById(vi.mocked(LineLayer), "solidarity-lines")).toHaveLength(0);
  });

  it("renders a solidarity-line layer when mapData carries a resolvable edge", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "T-a", h3_index: "872a3072cffffff" }),
        makeTerritory({ id: "T-b", h3_index: "872a3072dffffff" }),
      ],
    });
    const mapData = {
      type: "FeatureCollection" as const,
      features: [],
      metadata: {
        solidarity_edges: [
          makeSolidarityEdgeLine({
            source: "C001",
            target: "C002",
            source_territory: "T-a",
            target_territory: "T-b",
            solidarity_strength: 0.6,
          }),
        ],
      },
    };

    render(<DeckGLMap snapshot={snapshot} mapData={mapData} lens={{ kind: "heat" }} />);

    expect(layerCallsById(vi.mocked(LineLayer), "solidarity-lines")).toHaveLength(1);
    const props = layerCallsById(vi.mocked(LineLayer), "solidarity-lines")[0];
    expect(props?.data as unknown[]).toHaveLength(1);
  });

  it("an edge with a null territory is honestly dropped — no fabricated line", () => {
    const snapshot = makeSnapshot();
    const mapData = {
      type: "FeatureCollection" as const,
      features: [],
      metadata: {
        solidarity_edges: [makeSolidarityEdgeLine({ source_territory: null })],
      },
    };
    render(<DeckGLMap snapshot={snapshot} mapData={mapData} lens={{ kind: "heat" }} />);
    expect(layerCallsById(vi.mocked(LineLayer), "solidarity-lines")).toHaveLength(0);
  });
});

describe("DeckGLMap — solidarity lines survive the frozen region-map mount", () => {
  it("MapStage still exposes region-map, and the solidarity-line layer renders inside it, when /map/ carries solidarity_edges", async () => {
    useStore.setState((s) => ({ world: { ...s.world, snapshot: makeSnapshot() } }));
    server.use(
      http.get("/api/games/:id/map/", () =>
        HttpResponse.json({
          status: "ok",
          data: {
            type: "FeatureCollection",
            features: [],
            metadata: {
              solidarity_edges: [
                makeSolidarityEdgeLine({
                  source_territory: "territory-downtown",
                  target_territory: "territory-suburbs",
                }),
              ],
            },
          },
        }),
      ),
    );

    render(<MapStage gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("region-map")).toBeInTheDocument();
    await waitFor(() =>
      expect(layerCallsById(vi.mocked(LineLayer), "solidarity-lines")).toHaveLength(1),
    );
    // The frozen testid is still the one true map mount point, unchanged.
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
  });
});
