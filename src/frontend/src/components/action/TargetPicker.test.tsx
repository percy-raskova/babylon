/**
 * TargetPicker — per-row expected-delta chips (spec-116 FR-116-4.4).
 * Pins the honest-null convention shared with VerbForm's DeltaChip:
 * rows without expectedDeltas render label+group only; a zero/absent
 * axis renders no chip; ▲ gold / ▼ crimson by sign.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { VerbTarget } from "@/lib/verbs";
import { TargetPicker } from "./TargetPicker";

function renderPicker(targets: VerbTarget[]): ReturnType<typeof vi.fn> {
  const onSelect = vi.fn();
  render(
    <TargetPicker
      targets={targets}
      loading={false}
      error={null}
      selectedId={null}
      onSelect={onSelect}
    />,
  );
  return onSelect;
}

describe("TargetPicker expected-delta chips", () => {
  it("renders no chips for rows without expectedDeltas (honest null)", () => {
    renderPicker([{ id: "t1", label: "Downtown" }]);
    expect(screen.queryByTestId("target-delta")).not.toBeInTheDocument();
  });

  it("renders gold for a positive CI delta and crimson for a negative heat delta", () => {
    renderPicker([
      { id: "t1", label: "Downtown", expectedDeltas: { consciousness: 0.0123, heat: -0.05 } },
    ]);
    const chips = screen.getAllByTestId("target-delta");
    expect(chips).toHaveLength(2);
    expect(chips[0]).toHaveTextContent("▲CI +0.0123");
    expect(chips[0]!.className).toContain("text-accent-gold");
    expect(chips[1]).toHaveTextContent("▼Heat -0.05");
    expect(chips[1]!.className).toContain("text-accent-crimson");
  });

  it("hides zero axes and keeps the row clickable", async () => {
    const onSelect = renderPicker([
      { id: "t1", label: "Downtown", expectedDeltas: { consciousness: 0, heat: 0.1 } },
    ]);
    expect(screen.getAllByTestId("target-delta")).toHaveLength(1);
    await userEvent.click(screen.getByText("Downtown"));
    expect(onSelect).toHaveBeenCalledWith("t1");
  });
});
