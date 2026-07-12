/**
 * Unit tests for FloatingPanel (architecture §1.3) — the one primitive
 * every chrome overlay instances. TDD red phase written before the
 * implementation.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FloatingPanel } from "./FloatingPanel";

describe("FloatingPanel", () => {
  it("renders its testId on the root and its children", () => {
    render(
      <FloatingPanel anchor="left" testId="test-panel">
        <p>panel body</p>
      </FloatingPanel>,
    );
    expect(screen.getByTestId("test-panel")).toBeInTheDocument();
    expect(screen.getByText("panel body")).toBeInTheDocument();
  });

  it.each([
    ["left", "left-0"],
    ["right", "right-0"],
    ["top", "top-0"],
    ["bottom", "bottom-0"],
  ] as const)("anchor=%s applies its edge-docking class", (anchor, expectedClass) => {
    render(
      <FloatingPanel anchor={anchor} testId="anchored-panel">
        <span>x</span>
      </FloatingPanel>,
    );
    expect(screen.getByTestId("anchored-panel").className).toContain(expectedClass);
  });

  it("anchor='free' applies no edge-docking class (caller positions it)", () => {
    render(
      <FloatingPanel anchor="free" testId="free-panel">
        <span>x</span>
      </FloatingPanel>,
    );
    const el = screen.getByTestId("free-panel");
    expect(el.className).not.toMatch(/\b(left|right|top|bottom)-0\b/);
  });

  it("re-enables pointer-events-auto so it stays clickable inside the pointer-events-none chrome layer", () => {
    render(
      <FloatingPanel anchor="right" testId="clickable-panel">
        <span>x</span>
      </FloatingPanel>,
    );
    expect(screen.getByTestId("clickable-panel").className).toContain("pointer-events-auto");
  });

  it("renders no header when neither title nor onToggle is given", () => {
    render(
      <FloatingPanel anchor="left" testId="headerless-panel">
        <span>x</span>
      </FloatingPanel>,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders the title when given", () => {
    render(
      <FloatingPanel anchor="left" title="Outliner" testId="titled-panel">
        <span>x</span>
      </FloatingPanel>,
    );
    expect(screen.getByText("Outliner")).toBeInTheDocument();
  });

  it("keeps children mounted in the DOM while collapsed (hidden, not unmounted)", () => {
    render(
      <FloatingPanel
        anchor="left"
        title="Trends"
        collapsed
        onToggle={() => {}}
        testId="collapsible"
      >
        <p data-testid="child-content">still here</p>
      </FloatingPanel>,
    );
    const child = screen.getByTestId("child-content");
    expect(child).toBeInTheDocument();
    // Hidden via CSS on an ancestor, never JSX-unmounted (the always-mounted
    // rule this primitive must preserve for tick-fanned-out panels).
    expect(child.closest(".hidden")).not.toBeNull();
  });

  it("shows children when not collapsed", () => {
    render(
      <FloatingPanel
        anchor="left"
        title="Trends"
        collapsed={false}
        onToggle={() => {}}
        testId="expanded"
      >
        <p data-testid="child-content">visible</p>
      </FloatingPanel>,
    );
    expect(screen.getByTestId("child-content").closest(".hidden")).toBeNull();
  });

  it("calls onToggle when the toggle button is clicked, and reflects aria-expanded", async () => {
    const onToggle = vi.fn();
    render(
      <FloatingPanel
        anchor="left"
        title="Outliner"
        collapsed={false}
        onToggle={onToggle}
        testId="toggle-panel"
      >
        <span>x</span>
      </FloatingPanel>,
    );
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(button);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("applies a custom width style when given", () => {
    render(
      <FloatingPanel anchor="left" width={280} testId="wide-panel">
        <span>x</span>
      </FloatingPanel>,
    );
    expect(screen.getByTestId("wide-panel")).toHaveStyle({ width: "280px" });
  });
});
