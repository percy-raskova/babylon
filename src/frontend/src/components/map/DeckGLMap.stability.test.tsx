/**
 * Referential-stability contract for DeckGLMap's derived `layers` prop
 * (spec-112 C5-2). `worldSlice.fetchState` now keeps `world.snapshot`
 * referentially stable across identical same-tick heartbeat payloads (see
 * `worldSlice.test.ts`) — this is the other half of that fix: given
 * unchanged `snapshot`/`lens` props across a re-render, DeckGLMap's own
 * `useMemo` chain (territories -> hasH3/lensResult/getColor -> layers)
 * must return the SAME `layers` array, or deck.gl still rebuilds its GPU
 * fill-color buffer on every 2s beat regardless of the store-level fix.
 *
 * Deck.gl/maplibre mocked in setup.ts (same test double DeckGLMap.test.tsx
 * uses) — `DeckGL` is a `vi.fn` that renders its children, so its captured
 * call args expose the real `layers` array DeckGLMap computed for that
 * render.
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { DeckGLMap } from "./DeckGLMap";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";
import { DeckGL } from "@deck.gl/react";
import type { Lens } from "@/lib/lens";

/** Minimal shape of the mocked `DeckGL`'s captured props — just `layers`. */
interface DeckGLMockProps {
  layers: unknown[];
}

/** The `layers` array from the most recent render DeckGL was called with. */
function latestDeckGLLayers(): unknown[] {
  const mock = DeckGL as unknown as { mock: { calls: [DeckGLMockProps][] } };
  const calls = mock.mock.calls;
  const lastCall = calls[calls.length - 1];
  if (!lastCall) throw new Error("DeckGL mock was never called");
  return lastCall[0].layers;
}

describe("DeckGLMap — layers referential stability", () => {
  it("keeps the same layers array reference across a re-render with unchanged snapshot/lens", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "terr-1", name: "Downtown" }),
        makeTerritory({ id: "terr-2", name: "Suburbs" }),
      ],
    });
    const lens: Lens = { kind: "stance" };

    const { rerender } = render(<DeckGLMap snapshot={snapshot} lens={lens} />);
    const firstLayers = latestDeckGLLayers();

    // Same `snapshot`/`lens` object references, no other props — the
    // scenario a heartbeat that dedupes the snapshot (worldSlice.test.ts)
    // produces.
    rerender(<DeckGLMap snapshot={snapshot} lens={lens} />);
    const secondLayers = latestDeckGLLayers();

    expect(secondLayers).toBe(firstLayers);
  });

  it("builds a new layers array when the lens actually changes", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "terr-1", name: "Downtown" })],
    });

    const { rerender } = render(<DeckGLMap snapshot={snapshot} lens={{ kind: "stance" }} />);
    const firstLayers = latestDeckGLLayers();

    rerender(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} />);
    const secondLayers = latestDeckGLLayers();

    // Guard against a memoization bug that over-suppresses rebuilds: a
    // genuine lens change must still produce a new layers array.
    expect(secondLayers).not.toBe(firstLayers);
  });
});
