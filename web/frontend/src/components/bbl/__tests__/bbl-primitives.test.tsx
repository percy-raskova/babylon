/**
 * Tests for Babylon design system primitives (components/bbl).
 *
 * Covers: render, prop forwarding, slot composition, interactive states.
 */

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  BblLabel,
  BblData,
  BblPanel,
  BblBadge,
  BblTooltip,
  Sparkline,
  Gauge,
  Stat,
} from "@/components/bbl";

// ---------------------------------------------------------------------------
// BblLabel
// ---------------------------------------------------------------------------
describe("BblLabel", () => {
  it("renders children text", () => {
    render(<BblLabel>HEAT</BblLabel>);
    expect(screen.getByText("HEAT")).toBeInTheDocument();
  });

  it("applies custom color via style", () => {
    const { container } = render(<BblLabel color="#ff0000">X</BblLabel>);
    const el = container.firstElementChild as HTMLElement;
    expect(el.style.color).toBe("rgb(255, 0, 0)");
  });

  it("has uppercase tracking class", () => {
    const { container } = render(<BblLabel>TEST</BblLabel>);
    const el = container.firstElementChild as HTMLElement;
    expect(el.className).toContain("uppercase");
  });
});

// ---------------------------------------------------------------------------
// BblData
// ---------------------------------------------------------------------------
describe("BblData", () => {
  it("renders numeric children", () => {
    render(<BblData>42.3</BblData>);
    expect(screen.getByText("42.3")).toBeInTheDocument();
  });

  it("applies color and font-size via style", () => {
    const { container } = render(
      <BblData color="#40c040" size={14}>
        99
      </BblData>,
    );
    const el = container.firstElementChild as HTMLElement;
    expect(el.style.color).toBe("rgb(64, 192, 64)");
    expect(el.style.fontSize).toBe("14px");
  });
});

// ---------------------------------------------------------------------------
// BblPanel
// ---------------------------------------------------------------------------
describe("BblPanel", () => {
  it("renders body children", () => {
    render(<BblPanel>Panel content</BblPanel>);
    expect(screen.getByText("Panel content")).toBeInTheDocument();
  });

  it("renders title in header when provided", () => {
    render(<BblPanel title="Resources">Body</BblPanel>);
    expect(screen.getByText("Resources")).toBeInTheDocument();
  });

  it("renders right slot when title is present", () => {
    render(
      <BblPanel title="Stats" right={<span data-testid="right-slot">⚙</span>}>
        Body
      </BblPanel>,
    );
    expect(screen.getByTestId("right-slot")).toBeInTheDocument();
  });

  it("does not render header when no title", () => {
    const { container } = render(<BblPanel>No header</BblPanel>);
    // Should only have the body div, no header div
    const children = container.firstElementChild?.children;
    expect(children?.length).toBe(1);
  });

  it("applies accent border color", () => {
    const { container } = render(<BblPanel accent="#e04040">Body</BblPanel>);
    const el = container.firstElementChild as HTMLElement;
    expect(el.style.border).toContain("rgb(224, 64, 64)");
  });
});

// ---------------------------------------------------------------------------
// BblBadge
// ---------------------------------------------------------------------------
describe("BblBadge", () => {
  it("renders children", () => {
    render(<BblBadge>ALLIED</BblBadge>);
    expect(screen.getByText("ALLIED")).toBeInTheDocument();
  });

  it("applies custom color", () => {
    const { container } = render(<BblBadge color="#e04040">ENEMY</BblBadge>);
    const el = container.firstElementChild as HTMLElement;
    expect(el.style.color).toBe("rgb(224, 64, 64)");
  });

  it("has pill shape class", () => {
    const { container } = render(<BblBadge>TAG</BblBadge>);
    const el = container.firstElementChild as HTMLElement;
    expect(el.className).toContain("rounded-full");
  });
});

// ---------------------------------------------------------------------------
// BblTooltip
// ---------------------------------------------------------------------------
describe("BblTooltip", () => {
  it("renders children without tooltip content when no text/breakdown", () => {
    render(
      <BblTooltip>
        <span>Target</span>
      </BblTooltip>,
    );
    expect(screen.getByText("Target")).toBeInTheDocument();
  });

  it("shows tooltip text on mouse enter", () => {
    render(
      <BblTooltip text="Heat measures state repression exposure">
        <span>HEAT</span>
      </BblTooltip>,
    );
    fireEvent.mouseEnter(screen.getByText("HEAT"));
    expect(screen.getByText("Heat measures state repression exposure")).toBeInTheDocument();
  });

  it("hides tooltip on mouse leave", () => {
    render(
      <BblTooltip text="Info">
        <span>Hover me</span>
      </BblTooltip>,
    );
    fireEvent.mouseEnter(screen.getByText("Hover me"));
    expect(screen.getByText("Info")).toBeInTheDocument();
    fireEvent.mouseLeave(screen.getByText("Hover me"));
    expect(screen.queryByText("Info")).not.toBeInTheDocument();
  });

  it("renders breakdown entries on hover", () => {
    const breakdown = [
      { label: "Base", value: 0.2 },
      { label: "Informant penalty", value: 0.12 },
    ];
    render(
      <BblTooltip breakdown={breakdown} total={0.32}>
        <span>Value</span>
      </BblTooltip>,
    );
    fireEvent.mouseEnter(screen.getByText("Value"));
    expect(screen.getByText("Base")).toBeInTheDocument();
    expect(screen.getByText("Informant penalty")).toBeInTheDocument();
    expect(screen.getByText("Breakdown")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Sparkline
// ---------------------------------------------------------------------------
describe("Sparkline", () => {
  it("renders SVG polyline with data", () => {
    const { container } = render(<Sparkline data={[0.1, 0.3, 0.2, 0.5]} />);
    const polyline = container.querySelector("polyline");
    expect(polyline).toBeInTheDocument();
    expect(polyline?.getAttribute("points")).toBeTruthy();
  });

  it("renders label and value when provided", () => {
    render(<Sparkline data={[0.1, 0.5]} label="HEAT" value={0.5} />);
    expect(screen.getByText("HEAT")).toBeInTheDocument();
    expect(screen.getByText("0.500")).toBeInTheDocument();
  });

  it("returns null for empty data", () => {
    const { container } = render(<Sparkline data={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Gauge
// ---------------------------------------------------------------------------
describe("Gauge", () => {
  it("renders label and value", () => {
    render(<Gauge label="CL" value={8.4} max={12} color="#80b0e0" />);
    expect(screen.getByText("CL")).toBeInTheDocument();
    // Value text includes the /max
    expect(screen.getByText(/8\.4/)).toBeInTheDocument();
  });

  it("renders progress bar proportional to value/max", () => {
    const { container } = render(<Gauge label="SL" value={6} max={12} color="#40c040" />);
    const bar = container.querySelector("[class*='rounded-full']");
    // The inner progress bar should exist
    expect(bar).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Stat
// ---------------------------------------------------------------------------
describe("Stat", () => {
  it("renders label and value", () => {
    render(<Stat label="Cohesion" value="71%" color="#c8a860" />);
    expect(screen.getByText("Cohesion")).toBeInTheDocument();
    expect(screen.getByText("71%")).toBeInTheDocument();
  });

  it("wraps in tooltip when tooltip prop provided", () => {
    render(<Stat label="Heat" value="0.71" color="#e04040" tooltip="Repression exposure" />);
    // Should have cursor-help from tooltip wrapper
    const wrapper = screen.getByText("Heat").closest(".cursor-help");
    expect(wrapper).toBeInTheDocument();
  });
});
