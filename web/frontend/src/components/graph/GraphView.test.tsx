/**
 * Unit tests for the GraphView component (stubbed — Sigma.js mocked in setup.ts).
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { GraphView } from "./GraphView";
import { makeSnapshot, makeEntity, makeTerritory, makeEdge } from "@/test/fixtures";

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

  it("renders legend items", () => {
    const snapshot = makeSnapshot();
    const { container } = render(<GraphView snapshot={snapshot} />);
    // GraphLegend renders inside SigmaContainer
    // Since Sigma is mocked, the legend should still be in the DOM
    const legendText = container.textContent ?? "";
    expect(legendText).toContain("Entity");
    expect(legendText).toContain("Territory");
  });
});
