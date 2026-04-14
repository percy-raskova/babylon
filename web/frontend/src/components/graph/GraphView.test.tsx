/**
 * Unit tests for the GraphView component (stubbed — Sigma.js mocked in setup.ts).
 *
 * Updated for Spec 052: no entities, edges use mode enum.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { GraphView } from "./GraphView";
import { makeSnapshot, makeOrg, makeTerritory, makeEdge } from "@/test/fixtures";

// Enhance useSigma mock to support the methods EdgeFilter calls
vi.mock("@react-sigma/core", () => ({
  SigmaContainer: vi.fn(({ children }: { children?: React.ReactNode }) => children),
  useLoadGraph: vi.fn(() => vi.fn()),
  useRegisterEvents: vi.fn(() => vi.fn()),
  useSigma: vi.fn(() => ({
    getGraph: vi.fn(() => ({
      forEachEdge: vi.fn(),
    })),
    setSetting: vi.fn(),
    refresh: vi.fn(),
  })),
}));

describe("GraphView", () => {
  it("renders without crashing with empty snapshot", () => {
    const snapshot = makeSnapshot({
      territories: [],
      organizations: [],
      institutions: [],
      edges: [],
      hyperedges: [],
    });
    const { container } = render(<GraphView snapshot={snapshot} />);
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders with populated snapshot", () => {
    const snapshot = makeSnapshot({
      organizations: [
        makeOrg({ id: "o1", name: "Workers" }),
        makeOrg({ id: "o2", name: "Capitalists" }),
      ],
      territories: [makeTerritory({ id: "t1" })],
      edges: [makeEdge({ source_id: "o1", target_id: "o2", mode: "EXTRACTIVE" })],
    });
    const { container } = render(<GraphView snapshot={snapshot} />);
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders edge filter buttons", () => {
    const snapshot = makeSnapshot({
      edges: [
        makeEdge({
          source_id: "org-finance-bloc",
          target_id: "org-workers-union",
          mode: "EXTRACTIVE",
        }),
        makeEdge({
          id: "e2",
          source_id: "org-workers-union",
          target_id: "territory-downtown",
          mode: "SOLIDARISTIC",
        }),
      ],
    });
    render(<GraphView snapshot={snapshot} />);
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("EXTRACTIVE")).toBeInTheDocument();
    expect(screen.getByText("SOLIDARISTIC")).toBeInTheDocument();
  });

  it("renders legend items (no Entity)", () => {
    const snapshot = makeSnapshot();
    const { container } = render(<GraphView snapshot={snapshot} />);
    const legendText = container.textContent ?? "";
    expect(legendText).not.toContain("Entity");
    expect(legendText).toContain("Territory");
    expect(legendText).toContain("Organization");
    expect(legendText).toContain("Institution");
  });
});
