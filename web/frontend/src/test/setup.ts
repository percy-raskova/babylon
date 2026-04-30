/**
 * Vitest global setup — browser API mocks, MSW server, and Zustand reset.
 */

import "@testing-library/jest-dom/vitest";
import "vitest-canvas-mock";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { server } from "./server";
import { useGameStore } from "@/stores/gameStore";
import { useUIStore } from "@/stores/uiStore";
import { useMapStore } from "@/stores/mapStore";

// ---------------------------------------------------------------------------
// Browser API stubs (JSDOM missing these)
// ---------------------------------------------------------------------------

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

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

// crypto.randomUUID — already available in Node 19+, stub for safety
if (!globalThis.crypto?.randomUUID) {
  vi.stubGlobal("crypto", {
    ...globalThis.crypto,
    randomUUID: () => "00000000-0000-4000-8000-000000000000",
  });
}

// ---------------------------------------------------------------------------
// Heavy library mocks (deck.gl, maplibre, sigma)
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
}));

vi.mock("@react-sigma/core", () => ({
  SigmaContainer: vi.fn(({ children }: { children?: React.ReactNode }) => children),
  useLoadGraph: vi.fn(() => vi.fn()),
  useRegisterEvents: vi.fn(() => vi.fn()),
  useSigma: vi.fn(() => ({
    getGraph: vi.fn(() => ({
      forEachEdge: vi.fn(),
      getNodeAttribute: vi.fn(),
    })),
    setSetting: vi.fn(),
    refresh: vi.fn(),
  })),
}));

vi.mock("graphology-layout-forceatlas2", () => ({
  default: { assign: vi.fn() },
  assign: vi.fn(),
}));

// ---------------------------------------------------------------------------
// MSW server lifecycle
// ---------------------------------------------------------------------------

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ---------------------------------------------------------------------------
// Zustand store reset + RTL cleanup after each test
// ---------------------------------------------------------------------------

afterEach(() => {
  cleanup();
  // Reset stores to initial data values without wiping action functions.
  // Zustand's setState with replace=false merges, preserving functions.
  useGameStore.setState({
    sessionId: null,
    snapshot: null,
    available: [],
    tickSummaries: [],
    loading: false,
    error: null,
  });
  useUIStore.setState({
    selectedNodeId: null,
    selectedHexId: null,
    hoveredNodeId: null,
    rightPanelOpen: true,
    bottomPanelOpen: true,
    bottomTab: "timeseries" as const,
    pendingVerb: null,
    pendingOrgId: null,
    pendingTargetId: null,
    pendingParams: {},
    // Feature 042 resets
    activeLens: "political" as const,
    breadcrumbs: [],
    notifications: [],
    unreadCount: 0,
    notificationGroupsForTick: [],
    rightPanelWidth: 360,
    bottomPanelHeight: 260,
    pinnedIndicators: [
      "avg_consciousness",
      "avg_heat",
      "avg_organization",
      "imperial_rent",
    ] as const,
  });
  useMapStore.setState({
    activeLayer: "heat" as const,
    layerOpacity: 0.8,
    showEdges: false,
    lensOverride: false,
  });
});
