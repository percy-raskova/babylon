import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InspectionCard } from "./InspectionCard";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import type { InspectionFrame } from "@/store/slices/inspectSlice";

beforeEach(() => {
  resetStore();
});

function frame(overrides?: Partial<InspectionFrame>): InspectionFrame {
  return {
    ref: { kind: "org", id: "org-1" },
    data: null,
    loading: false,
    error: null,
    pinned: false,
    fetchedAtTick: null,
    ...overrides,
  };
}

describe("InspectionCard", () => {
  it("shows a loading state", () => {
    render(
      <InspectionCard
        frame={frame({ loading: true })}
        canDrill
        onDrill={vi.fn()}
        onTogglePin={vi.fn()}
      />,
    );
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows a loud error (Constitution III.11)", () => {
    render(
      <InspectionCard
        frame={frame({ error: "Org not found" })}
        canDrill
        onDrill={vi.fn()}
        onTogglePin={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Org not found");
  });

  it("shows an honest no-data state when resolution succeeded with nothing to show", () => {
    render(<InspectionCard frame={frame()} canDrill onDrill={vi.fn()} onTogglePin={vi.fn()} />);
    expect(screen.getByTestId("inspection-no-data")).toBeInTheDocument();
  });

  it("renders the resolved node via FormulaCard", () => {
    render(
      <InspectionCard
        frame={frame({
          data: {
            ref: { kind: "org", id: "org-1" },
            title: "Wayne County Committee",
            sections: [{ rows: [{ label: "Cohesion", value: 0.6, format: "decimal2" }] }],
          },
        })}
        canDrill
        onDrill={vi.fn()}
        onTogglePin={vi.fn()}
      />,
    );
    expect(screen.getByText("Wayne County Committee")).toBeInTheDocument();
    expect(screen.getByTestId("formula-card")).toBeInTheDocument();
  });

  it("renders the 'act' link for org/hex subjects, and calls ui.toggleComposer on click", () => {
    render(
      <InspectionCard
        frame={frame({ ref: { kind: "org", id: "org-1" } })}
        canDrill
        onDrill={vi.fn()}
        onTogglePin={vi.fn()}
      />,
    );
    const before = useStore.getState().ui.chrome.composerOpen;
    fireEvent.click(screen.getByTestId("inspection-act"));
    expect(useStore.getState().ui.chrome.composerOpen).toBe(!before);
  });

  it("does not render the 'act' link for a metric subject", () => {
    render(
      <InspectionCard
        frame={frame({ ref: { kind: "metric", id: "profit_rate", scope: "global" } })}
        canDrill
        onDrill={vi.fn()}
        onTogglePin={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("inspection-act")).not.toBeInTheDocument();
  });

  it("toggles pin via the pin button", () => {
    const onTogglePin = vi.fn();
    render(<InspectionCard frame={frame()} canDrill onDrill={vi.fn()} onTogglePin={onTogglePin} />);
    fireEvent.click(screen.getByTestId("inspection-pin"));
    expect(onTogglePin).toHaveBeenCalledOnce();
  });

  it("shows the depth-limit notice when canDrill is false", () => {
    render(
      <InspectionCard frame={frame()} canDrill={false} onDrill={vi.fn()} onTogglePin={vi.fn()} />,
    );
    expect(screen.getByTestId("depth-limit-notice")).toBeInTheDocument();
  });
});
