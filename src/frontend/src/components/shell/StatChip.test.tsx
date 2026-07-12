import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatChip } from "./StatChip";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";

beforeEach(() => {
  resetStore();
});

describe("StatChip", () => {
  it("renders 'no data' honestly for a null value (Constitution III.11)", () => {
    render(<StatChip label="Profit" value={null} format={(v) => v.toFixed(3)} />);
    expect(screen.getByText("no data")).toBeInTheDocument();
  });

  it("renders a plain non-clickable chip (a <div>) when no metric prop is given — existing call sites keep working", () => {
    render(<StatChip label="Pop" value={42000} format={(v) => v.toLocaleString()} />);
    const chip = screen.getByTestId("stat-pop");
    expect(chip.tagName).toBe("DIV");
    expect(screen.getByText("42,000")).toBeInTheDocument();
  });

  it("renders a clickable button and pushes a metric InspectionRef when metric is given", () => {
    render(
      <StatChip label="Rent Φ" value={12.5} format={(v) => v.toFixed(2)} metric="imperial_rent" />,
    );
    const chip = screen.getByTestId("stat-rent φ");
    expect(chip.tagName).toBe("BUTTON");

    fireEvent.click(chip);
    expect(useStore.getState().inspect.stack).toHaveLength(1);
    expect(useStore.getState().inspect.stack[0]?.ref).toEqual({
      kind: "metric",
      id: "imperial_rent",
      scope: "global",
      label: "Rent Φ",
    });
  });

  it("honors an explicit scope override", () => {
    render(
      <StatChip
        label="Profit"
        value={0.08}
        format={(v) => v.toFixed(3)}
        metric="profit_rate"
        scope="hex:87283"
      />,
    );
    fireEvent.click(screen.getByTestId("stat-profit"));
    expect(useStore.getState().inspect.stack[0]?.ref.scope).toBe("hex:87283");
  });
});
