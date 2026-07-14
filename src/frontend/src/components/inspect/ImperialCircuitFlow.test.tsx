import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ImperialCircuitFlow } from "./ImperialCircuitFlow";
import type { CircuitFlows } from "@/types/inspection";

describe("ImperialCircuitFlow", () => {
  const fullCircuit: CircuitFlows = {
    nodes: [
      { role: "periphery_proletariat", id: "C001", name: "Periphery Worker" },
      { role: "comprador_bourgeoisie", id: "C002", name: "Comprador" },
      { role: "core_bourgeoisie", id: "C003", name: "Core Bourgeoisie" },
      { role: "labor_aristocracy", id: "C004", name: "Labor Aristocracy" },
    ],
    links: [
      {
        source_role: "periphery_proletariat",
        target_role: "comprador_bourgeoisie",
        source_id: "C001",
        target_id: "C002",
        value_flow: 2.0,
      },
      {
        source_role: "comprador_bourgeoisie",
        target_role: "core_bourgeoisie",
        source_id: "C002",
        target_id: "C003",
        value_flow: 5.0,
      },
      {
        source_role: "core_bourgeoisie",
        target_role: "labor_aristocracy",
        source_id: "C003",
        target_id: "C004",
        value_flow: 1.0,
      },
    ],
  };

  it("renders one node marker per circuit node", () => {
    render(<ImperialCircuitFlow data={fullCircuit} />);
    for (const node of fullCircuit.nodes) {
      expect(screen.getByTestId(`circuit-flow-node-${node.id}`)).toBeInTheDocument();
    }
  });

  it("renders one link ribbon per circuit link", () => {
    render(<ImperialCircuitFlow data={fullCircuit} />);
    for (const link of fullCircuit.links) {
      expect(
        screen.getByTestId(`circuit-flow-link-${link.source_id}-${link.target_id}`),
      ).toBeInTheDocument();
    }
  });

  it("scales ribbon thickness with value_flow", () => {
    render(<ImperialCircuitFlow data={fullCircuit} />);
    const thin = screen.getByTestId("circuit-flow-link-C001-C002"); // 2.0
    const thick = screen.getByTestId("circuit-flow-link-C002-C003"); // 5.0 (max)
    const thinWidth = Number(thin.getAttribute("stroke-width"));
    const thickWidth = Number(thick.getAttribute("stroke-width"));
    expect(thickWidth).toBeGreaterThan(thinWidth);
  });

  it("omits a node/link the backend never sent (partial circuit, e.g. wayne_county)", () => {
    const partial: CircuitFlows = {
      nodes: [
        { role: "periphery_proletariat", id: "C004", name: "Dearborn Industrial Workers" },
        { role: "core_bourgeoisie", id: "C003", name: "Wayne County Bourgeoisie" },
        { role: "labor_aristocracy", id: "C002", name: "Suburban Petty Bourgeoisie" },
      ],
      links: [
        {
          source_role: "core_bourgeoisie",
          target_role: "labor_aristocracy",
          source_id: "C003",
          target_id: "C002",
          value_flow: 1.0,
        },
      ],
    };
    render(<ImperialCircuitFlow data={partial} />);
    expect(screen.queryByTestId("circuit-flow-node-C001")).not.toBeInTheDocument();
    expect(screen.getAllByTestId(/^circuit-flow-node-/)).toHaveLength(3);
    expect(screen.getAllByTestId(/^circuit-flow-link-/)).toHaveLength(1);
  });

  it("renders all-zero value_flow links with a visible minimum thickness, not zero", () => {
    const allZero: CircuitFlows = {
      nodes: fullCircuit.nodes,
      links: fullCircuit.links.map((l) => ({ ...l, value_flow: 0.0 })),
    };
    render(<ImperialCircuitFlow data={allZero} />);
    for (const link of allZero.links) {
      const el = screen.getByTestId(`circuit-flow-link-${link.source_id}-${link.target_id}`);
      expect(Number(el.getAttribute("stroke-width"))).toBeGreaterThan(0);
    }
  });

  it("renders no link ribbons when links is empty", () => {
    render(<ImperialCircuitFlow data={{ nodes: fullCircuit.nodes, links: [] }} />);
    expect(screen.queryAllByTestId(/^circuit-flow-link-/)).toHaveLength(0);
  });
});
