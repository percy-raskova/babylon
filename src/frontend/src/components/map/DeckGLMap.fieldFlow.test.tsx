/**
 * DeckGLMap — the gradient-wind vector lens's data-fetch + honest-empty
 * wiring (DESIGN_BIBLE.md §11, Wave 3). Covers what `fieldFlow.test.ts`
 * can't: the `GET /field_state/` fetch is gated on the `field_flow` lens
 * actually being active, keyed on `[gameId, tick]`, and the legend's honest
 * "— no data" hint when the tick's edges are empty (Constitution III.11).
 *
 * deck.gl/maplibre mocked globally in setup.ts — `PathLayer`/`TripsLayer`/
 * `ScatterplotLayer` are plain `vi.fn()` stubs, so a layer's constructor
 * args are read off `.mock.calls` (mirrors `criticalPulse.test.ts`'s
 * `pulseLayerProps` idiom).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import { TripsLayer } from "@deck.gl/geo-layers";
import { server } from "@/test/server";
import { DeckGLMap } from "./DeckGLMap";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";
import {
  makeSnapshot,
  makeTerritory,
  makeFieldStatePayload,
  makeFieldStateEdge,
} from "@/test/fixtures";

/** Constructor-call props for the Nth (default last) call to a mocked deck.gl layer class. */
function layerCallProps(
  mockedClass: { mock: { calls: unknown[][] } },
  index = -1,
): Record<string, unknown> {
  const calls = mockedClass.mock.calls;
  const call = index < 0 ? calls.at(index) : calls[index];
  if (!call) throw new Error("layer class was never constructed");
  return call[0] as Record<string, unknown>;
}

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
  resetMockGameState();
  vi.mocked(PathLayer).mockClear();
  vi.mocked(ScatterplotLayer).mockClear();
  vi.mocked(TripsLayer).mockClear();
});

describe("DeckGLMap — field_flow lens fetch gating", () => {
  it("fetches GET /field_state/ when the field_flow lens is active and a gameId is provided", async () => {
    const snapshot = makeSnapshot();
    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "field_flow", field: "exploitation" }}
        gameId={DEFAULT_GAME_ID}
      />,
    );
    await waitFor(() => expect(requestLog).toContain("GET field_state"));
  });

  it("does NOT fetch GET /field_state/ for a different active lens (heat)", async () => {
    const snapshot = makeSnapshot();
    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} gameId={DEFAULT_GAME_ID} />);
    // Give any stray effect a tick to fire before asserting its absence.
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(requestLog).not.toContain("GET field_state");
  });

  it("does NOT fetch GET /field_state/ when no gameId is provided, even if field_flow is active", async () => {
    const snapshot = makeSnapshot();
    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "field_flow", field: "exploitation" }} />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(requestLog).not.toContain("GET field_state");
  });
});

describe("DeckGLMap — field_flow honest empty / real data rendering", () => {
  it("honest-empty: no field-flow layers, legend carries a '— no data' hint, when the tick's edges are empty (default handler)", async () => {
    const snapshot = makeSnapshot();
    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "field_flow", field: "exploitation" }}
        gameId={DEFAULT_GAME_ID}
      />,
    );

    await waitFor(() => expect(requestLog).toContain("GET field_state"));
    await waitFor(() =>
      expect(screen.getByTestId("lens-legend-label")).toHaveTextContent(/no data/i),
    );
    expect(layerCallsById(vi.mocked(PathLayer), "field-flow-static")).toHaveLength(0);
    expect(layerCallsById(vi.mocked(TripsLayer), "field-flow-trips")).toHaveLength(0);
  });

  it("renders the static dashed path + arrowhead + animated trail when field_state carries a resolvable edge", async () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "T-a", h3_index: "872a3072cffffff" }),
        makeTerritory({ id: "T-b", h3_index: "872a3072dffffff" }),
      ],
    });
    server.use(
      http.get("/api/games/:id/field_state/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeFieldStatePayload({
            edges: [
              makeFieldStateEdge({
                source_territory: "T-a",
                target_territory: "T-b",
                field: "exploitation",
                gradient: 0.6,
              }),
            ],
          }),
        }),
      ),
    );

    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "field_flow", field: "exploitation" }}
        gameId={DEFAULT_GAME_ID}
      />,
    );

    await waitFor(() =>
      expect(layerCallsById(vi.mocked(PathLayer), "field-flow-static")).toHaveLength(1),
    );
    expect(layerCallsById(vi.mocked(ScatterplotLayer), "field-flow-arrowheads")).toHaveLength(1);
    expect(layerCallsById(vi.mocked(TripsLayer), "field-flow-trips")).toHaveLength(1);

    const staticProps = layerCallProps(vi.mocked(PathLayer));
    expect(staticProps.data as unknown[]).toHaveLength(1);

    // Honest-present: no "— no data" suffix once a real edge resolved.
    await waitFor(() =>
      expect(screen.getByTestId("lens-legend-label")).not.toHaveTextContent(/no data/i),
    );
    expect(screen.getByTestId("lens-legend-label")).toHaveTextContent(/gradient wind/i);
  });

  it("an edge with a null territory is honestly dropped — still honest-empty, no fabricated arrow", async () => {
    const snapshot = makeSnapshot();
    server.use(
      http.get("/api/games/:id/field_state/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeFieldStatePayload({
            edges: [makeFieldStateEdge({ source_territory: null })],
          }),
        }),
      ),
    );

    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "field_flow", field: "exploitation" }}
        gameId={DEFAULT_GAME_ID}
      />,
    );

    await waitFor(() =>
      expect(screen.getByTestId("lens-legend-label")).toHaveTextContent(/no data/i),
    );
    expect(layerCallsById(vi.mocked(PathLayer), "field-flow-static")).toHaveLength(0);
  });
});
