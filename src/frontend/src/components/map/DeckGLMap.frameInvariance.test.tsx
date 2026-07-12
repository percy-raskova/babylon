/**
 * "One cartographic frame across lenses" contract (spec-113 Lane B,
 * DESIGN_BIBLE.md §2.2/§10: "lens switches change ONLY per-feature fill
 * functions; camera, projection, geometry identical pre/post switch").
 *
 * Two invariants, both checked at the deck.gl prop level (DeckGL mocked in
 * setup.ts; `@deck.gl/layers`/`@deck.gl/geo-layers` locally overridden here
 * — the county-hairline/state-border layers need an inspectable `.id`,
 * matching `layers/political.ts`'s own test's pattern):
 *
 * 1. `initialViewState` is the same object across a lens switch — trivially
 *    true structurally (it's never derived from `lens`), but pinned here as
 *    a regression guard against a future refactor threading lens into the
 *    view state.
 * 2. The political base layer objects (county hairlines, state borders) —
 *    real geometry, drawn "ALWAYS on" under every lens — keep their exact
 *    object identity across a lens switch: `politicalLayers`'s `useMemo`
 *    deps never include `lens`, so a fill-only change must not rebuild them
 *    (a rebuild would mean deck.gl re-uploads geometry to the GPU for a
 *    change that was never geometric — the DESIGN_BIBLE.md §6 perf risk).
 */

import { describe, it, expect, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { DeckGL } from "@deck.gl/react";
import { DeckGLMap } from "./DeckGLMap";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";

vi.mock("@deck.gl/geo-layers", () => ({
  H3HexagonLayer: vi.fn(),
  H3ClusterLayer: vi.fn(),
}));

vi.mock("@deck.gl/layers", () => {
  class GeoJsonLayer {
    id: string;
    constructor(props: Record<string, unknown>) {
      this.id = props.id as string;
    }
  }
  return { GeoJsonLayer, ScatterplotLayer: vi.fn(), PolygonLayer: vi.fn() };
});

interface DeckGLMockProps {
  layers: { id: string }[];
  initialViewState: unknown;
}

function latestDeckGLProps(): DeckGLMockProps {
  const mock = DeckGL as unknown as { mock: { calls: [DeckGLMockProps][] } };
  const calls = mock.mock.calls;
  const lastCall = calls[calls.length - 1];
  if (!lastCall) throw new Error("DeckGL mock was never called");
  return lastCall[0];
}

describe("DeckGLMap — one cartographic frame across lenses (DESIGN_BIBLE.md §2.2/§10)", () => {
  it("keeps initialViewState referentially identical across a lens switch", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "t1", h3_index: "872a3072cffffff" })],
    });
    const { rerender } = render(
      <DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="county" />,
    );
    const first = latestDeckGLProps().initialViewState;

    rerender(<DeckGLMap snapshot={snapshot} lens={{ kind: "habitability" }} framing="county" />);
    const second = latestDeckGLProps().initialViewState;

    expect(second).toBe(first);
  });

  it("keeps the political base layer objects referentially stable across a lens switch (geometry never rebuilt for a fill-only change)", async () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "t1", h3_index: "872a3072cffffff" })],
    });
    const { rerender } = render(
      <DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="county" />,
    );

    await waitFor(() => {
      const ids = latestDeckGLProps().layers.map((l) => l.id);
      expect(ids).toContain("political-county-hairlines");
      expect(ids).toContain("political-state-borders");
    });
    const firstLayers = latestDeckGLProps().layers;
    const firstHairline = firstLayers.find((l) => l.id === "political-county-hairlines");
    const firstStateBorder = firstLayers.find((l) => l.id === "political-state-borders");

    rerender(<DeckGLMap snapshot={snapshot} lens={{ kind: "habitability" }} framing="county" />);

    const secondLayers = latestDeckGLProps().layers;
    const secondHairline = secondLayers.find((l) => l.id === "political-county-hairlines");
    const secondStateBorder = secondLayers.find((l) => l.id === "political-state-borders");

    expect(secondHairline).toBe(firstHairline);
    expect(secondStateBorder).toBe(firstStateBorder);
  });

  it("keeps the political base layers stable across a framing (LOD) change too", async () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "t1", h3_index: "872a3072cffffff" })],
    });
    const { rerender } = render(
      <DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="county" />,
    );

    await waitFor(() => {
      const ids = latestDeckGLProps().layers.map((l) => l.id);
      expect(ids).toContain("political-county-hairlines");
    });
    const firstHairline = latestDeckGLProps().layers.find(
      (l) => l.id === "political-county-hairlines",
    );

    rerender(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="hex" />);

    const secondHairline = latestDeckGLProps().layers.find(
      (l) => l.id === "political-county-hairlines",
    );
    expect(secondHairline).toBe(firstHairline);
  });
});
