import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ValueRow } from "./ValueRow";
import type { InspectionRow } from "@/types/inspection";

describe("ValueRow", () => {
  it("renders 'no data' honestly for a null value (Constitution III.11)", () => {
    const row: InspectionRow = { label: "Habitability", value: null, format: "decimal2" };
    render(<ValueRow row={row} canDrill={true} onDrill={vi.fn()} />);
    expect(screen.getByText("no data")).toBeInTheDocument();
  });

  it("formats decimal3/percent/integer per BblFormat", () => {
    const { rerender } = render(
      <ValueRow
        row={{ label: "X", value: 0.45231, format: "decimal3" }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.getByText("0.452")).toBeInTheDocument();

    rerender(
      <ValueRow
        row={{ label: "X", value: 0.45231, format: "percent" }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.getByText("45.2%")).toBeInTheDocument();

    rerender(
      <ValueRow row={{ label: "X", value: 42000, format: "integer" }} canDrill onDrill={vi.fn()} />,
    );
    expect(screen.getByText("42,000")).toBeInTheDocument();
  });

  it("renders a clickable explain affordance when ref is present and canDrill is true", () => {
    const onDrill = vi.fn();
    const ref = { kind: "metric" as const, id: "profit_rate", scope: "global" };
    render(
      <ValueRow
        row={{ label: "Profit Rate", value: 0.08, format: "decimal3", ref }}
        canDrill
        onDrill={onDrill}
      />,
    );
    fireEvent.click(screen.getByTestId("explain-Profit Rate"));
    expect(onDrill).toHaveBeenCalledWith(ref);
  });

  it("shows the value dimmed with no click target when ref is present but canDrill is false (depth limit)", () => {
    const onDrill = vi.fn();
    const ref = { kind: "metric" as const, id: "profit_rate", scope: "global" };
    render(
      <ValueRow
        row={{ label: "Profit Rate", value: 0.08, format: "decimal3", ref }}
        canDrill={false}
        onDrill={onDrill}
      />,
    );
    expect(screen.queryByTestId("explain-Profit Rate")).not.toBeInTheDocument();
    expect(screen.getByText("0.080")).toBeInTheDocument();
  });

  it("renders a BreakdownBar instead of a plain value when composition is present", () => {
    render(
      <ValueRow
        row={{
          label: "Consciousness",
          value: null,
          format: "raw",
          composition: [{ key: "Revolutionary", value: 0.85 }],
        }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.getByTestId("breakdown-bar")).toBeInTheDocument();
  });

  it("renders a Sparkline with realized min/max labeled inline when history is present", () => {
    render(
      <ValueRow
        row={{ label: "Rent Φ", value: 12, format: "decimal2", history: [1, 5, 12] }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.getByTestId("history-Rent Φ")).toBeInTheDocument();
    expect(screen.getByText(/min 1.00 \/ max 12.00/)).toBeInTheDocument();
  });

  it("omits the history row when history is absent", () => {
    render(
      <ValueRow
        row={{ label: "Rent Φ", value: 12, format: "decimal2" }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("history-Rent Φ")).not.toBeInTheDocument();
  });

  it("renders a MockBadge next to the label when row.mock is true (Program 17 Wave 1 / W1.4)", () => {
    render(
      <ValueRow
        row={{ label: "Class Position", value: "Placeholder", format: "raw", mock: true }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.getByTestId("mock-badge")).toBeInTheDocument();
  });

  it("does not render a MockBadge when row.mock is absent", () => {
    render(
      <ValueRow
        row={{ label: "Wealth", value: 0.65, format: "decimal2" }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("mock-badge")).not.toBeInTheDocument();
  });

  it("renders an ImperialCircuitFlow instead of a plain value when circuitFlows is present (Program 17 Wave 1 / W1.6)", () => {
    render(
      <ValueRow
        row={{
          label: "Imperial Circuit",
          value: null,
          format: "raw",
          circuitFlows: {
            nodes: [{ role: "core_bourgeoisie", id: "C003", name: "Core Bourgeoisie" }],
            links: [],
          },
        }}
        canDrill
        onDrill={vi.fn()}
      />,
    );
    expect(screen.getByTestId("imperial-circuit-flow")).toBeInTheDocument();
  });
});
