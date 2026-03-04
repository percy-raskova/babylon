/**
 * Unit tests for the GraphView component (stubbed — Sigma.js mocked in setup.ts).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { GraphView } from "./GraphView";
import { makeSnapshot, makeEntity, makeTerritory, makeEdge } from "@/test/fixtures";

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
      entities: [],
      territories: [],
      edges: [],
    });
    const { container } = render(<GraphView snapshot={snapshot} />);
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders with populated snapshot", () => {
    const snapshot = makeSnapshot({
      entities: [
        makeEntity({ id: "e1", name: "Worker" }),
        makeEntity({ id: "e2", name: "Capitalist" }),
      ],
      territories: [makeTerritory({ id: "t1" })],
      edges: [makeEdge({ source_id: "e1", target_id: "e2" })],
    });
    const { container } = render(<GraphView snapshot={snapshot} />);
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders edge filter buttons", () => {
    const snapshot = makeSnapshot({
      edges: [
        makeEdge({ source_id: "e1", target_id: "e2", edge_type: "EXPLOITATION" }),
        makeEdge({ source_id: "e1", target_id: "e2", edge_type: "SOLIDARITY" }),
      ],
    });
    render(<GraphView snapshot={snapshot} />);
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("EXPLOITATION")).toBeInTheDocument();
    expect(screen.getByText("SOLIDARITY")).toBeInTheDocument();
  });

  it("renders legend items", () => {
    const snapshot = makeSnapshot();
    const { container } = render(<GraphView snapshot={snapshot} />);
    const legendText = container.textContent ?? "";
    expect(legendText).toContain("Entity");
    expect(legendText).toContain("Territory");
  });
});
