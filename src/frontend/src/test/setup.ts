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
}));

vi.mock("@deck.gl/layers", () => ({
  ScatterplotLayer: vi.fn(),
  PolygonLayer: vi.fn(),
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
