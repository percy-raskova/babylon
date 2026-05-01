/**
 * BreakdownTooltip tests.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BreakdownTooltip } from "@/components/inspector/BreakdownTooltip";
import type { ScriptValue, Scope, Breakdown, Contributor } from "@/lib/selectors/types";
import { makeWayneCountySnapshot } from "@/test/fixtures";

function makeMockSelector(breakdown: Breakdown): ScriptValue {
  return {
    name: "test.selector",
    label: "Test Metric",
    description: "A test metric.",
    scopeKind: "hex",
    evaluate: () => breakdown.total,
    breakdown: () => breakdown,
  };
}

function makeScope(): Scope {
  return { snapshot: makeWayneCountySnapshot(), this: { kind: "hex", id: "territory-downtown" } };
}

describe("BreakdownTooltip", () => {
  it("renders children as trigger", () => {
    const selector = makeMockSelector({ total: 0.5, contributors: [] });
    render(
      <BreakdownTooltip selector={selector} scope={makeScope()}>
        <span>0.50</span>
      </BreakdownTooltip>,
    );
    expect(screen.getByText("0.50")).toBeInTheDocument();
  });

  it("shows breakdown content on click", async () => {
    const user = userEvent.setup();
    const selector = makeMockSelector({
      total: 0.75,
      contributors: [
        {
          label: "Base Value",
          value: 0.75,
          share: 1.0,
          source: { kind: "snapshot_field", path: "territories[t1].heat" },
          children: [],
        },
      ],
    });

    render(
      <BreakdownTooltip selector={selector} scope={makeScope()}>
        <span>Click me</span>
      </BreakdownTooltip>,
    );

    await user.click(screen.getByRole("button", { name: /breakdown for test metric/i }));

    expect(await screen.findByText("Test Metric")).toBeInTheDocument();
    expect(screen.getByText("Base Value")).toBeInTheDocument();
    // The value 0.75 appears in both trigger and popover; verify at least 2 instances
    expect(screen.getAllByText("0.75").length).toBeGreaterThanOrEqual(2);
  });

  it("renders source labels correctly", async () => {
    const user = userEvent.setup();
    const selector = makeMockSelector({
      total: 1.0,
      contributors: [
        {
          label: "Snapshot Field",
          value: 0.6,
          share: 0.6,
          source: { kind: "snapshot_field", path: "territories[x].heat" },
          children: [],
        },
        {
          label: "Game Defines",
          value: 0.4,
          share: 0.4,
          source: { kind: "gamedefines", path: "GAMEDEFINES.HEAT_PENALTY" },
          children: [],
        },
      ],
    });

    render(
      <BreakdownTooltip selector={selector} scope={makeScope()}>
        <span>Trigger</span>
      </BreakdownTooltip>,
    );

    await user.click(screen.getByRole("button"));

    // Check that source kind prefixes are rendered
    expect(await screen.findByText(/📊.*heat/)).toBeInTheDocument();
    expect(screen.getByText(/⚙️.*HEAT_PENALTY/)).toBeInTheDocument();
  });

  it("renders recursive tree up to depth 4", async () => {
    const user = userEvent.setup();

    // Build a deep tree: depth 0 → 1 → 2 → 3 → 4 (depth 4 should NOT render)
    const leaf: Contributor = {
      label: "Depth 4 (should not render)",
      value: 0.1,
      share: 1.0,
      source: { kind: "snapshot_field", path: "deep" },
      children: [],
    };
    const d3: Contributor = {
      label: "Depth 3",
      value: 0.1,
      share: 1.0,
      source: { kind: "derived", path: "d3" },
      children: [leaf],
    };
    const d2: Contributor = {
      label: "Depth 2",
      value: 0.1,
      share: 1.0,
      source: { kind: "derived", path: "d2" },
      children: [d3],
    };
    const d1: Contributor = {
      label: "Depth 1",
      value: 0.1,
      share: 1.0,
      source: { kind: "derived", path: "d1" },
      children: [d2],
    };
    const root: Contributor = {
      label: "Depth 0",
      value: 0.1,
      share: 1.0,
      source: { kind: "derived", path: "d0" },
      children: [d1],
    };

    const selector = makeMockSelector({ total: 0.1, contributors: [root] });

    render(
      <BreakdownTooltip selector={selector} scope={makeScope()}>
        <span>Deep</span>
      </BreakdownTooltip>,
    );

    await user.click(screen.getByRole("button"));

    expect(await screen.findByText("Depth 0")).toBeInTheDocument();
    expect(screen.getByText("Depth 1")).toBeInTheDocument();
    expect(screen.getByText("Depth 2")).toBeInTheDocument();
    expect(screen.getByText("Depth 3")).toBeInTheDocument();
    // Depth 4 should be capped — not rendered
    expect(screen.queryByText("Depth 4 (should not render)")).not.toBeInTheDocument();
  });

  it("passes through children when scope is null", () => {
    const selector = makeMockSelector({ total: 0, contributors: [] });
    render(
      <BreakdownTooltip selector={selector} scope={null}>
        <span>No scope</span>
      </BreakdownTooltip>,
    );
    expect(screen.getByText("No scope")).toBeInTheDocument();
    // No button trigger when scope is null
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
