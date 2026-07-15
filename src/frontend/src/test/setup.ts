/**
 * Vitest global setup — MSW server lifecycle + heavy library mocks.
 *
 * The deck.gl/maplibre mocks (spec-110 B2) mirror
 * `web/frontend/src/test/setup.ts`: they stub out real WebGL/canvas
 * construction so map-component tests can run under jsdom without a GPU.
 * ResizeObserver/IntersectionObserver stubs are also jsdom gaps deck.gl's
 * dependency chain expects.
 */

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { server } from "./server";

// ---------------------------------------------------------------------------
// Browser API stubs (JSDOM missing these)
// ---------------------------------------------------------------------------

class ResizeObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

class IntersectionObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal("IntersectionObserver", IntersectionObserverStub);

// ---------------------------------------------------------------------------
// Heavy library mocks (deck.gl, maplibre) — no real WebGL/canvas in jsdom.
// ---------------------------------------------------------------------------

vi.mock("maplibre-gl", () => ({
  default: { Map: vi.fn() },
  Map: vi.fn(),
}));

vi.mock("react-map-gl/maplibre", () => ({
  default: vi.fn(({ children }: { children?: React.ReactNode }) => children),
  Map: vi.fn(({ children }: { children?: React.ReactNode }) => children),
}));

vi.mock("@deck.gl/react", () => ({
  DeckGL: vi.fn(({ children }: { children?: React.ReactNode }) => children),
}));

vi.mock("@deck.gl/geo-layers", () => ({
  H3HexagonLayer: vi.fn(),
  // Spec-113 Lane B: DeckGLMap's region-framing branch (and any leftover
  // async effect from an unmounted DeckGLMap — its topology `useEffect`
  // isn't awaited by every test) can construct an H3ClusterLayer even in
  // files that don't locally override this mock (that pattern,
  // e.g. DeckGLMap.test.tsx, still takes precedence for its own file).
  H3ClusterLayer: vi.fn(),
  // Wave 3 §11: DeckGLMap transitively imports fieldFlow.ts's TripsLayer
  // (the gradient-wind lens's animated trail) on every render, regardless of
  // the active lens — any test mounting a real DeckGLMap needs this stub,
  // not just fieldFlow.test.ts's own local override (which additionally
  // inspects `.id`/`.props`).
  TripsLayer: vi.fn(),
}));

vi.mock("@deck.gl/layers", () => ({
  ScatterplotLayer: vi.fn(),
  PolygonLayer: vi.fn(),
  // Spec-113 Lane B: layers/political.ts's base political-cartography stack
  // (county hairlines/state borders) is now part of every DeckGLMap render,
  // so any test mounting a real DeckGLMap needs this, not just political.test.ts's
  // own local override (which additionally inspects `.id`/`.props`).
  GeoJsonLayer: vi.fn(),
  // Wave 3 §11: fieldFlow.ts's static dashed base layer — same reasoning as
  // TripsLayer above.
  PathLayer: vi.fn(),
}));

// ---------------------------------------------------------------------------
// MSW server lifecycle
// ---------------------------------------------------------------------------

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => server.close());
