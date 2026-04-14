/**
 * Unit tests for the TargetSelector component.
 *
 * Updated for Spec 052: educate targets hyperedges, not entities.
 * Entity-level targets no longer exist.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TargetSelector } from "./TargetSelector";
import { makeSnapshot } from "@/test/fixtures";

describe("TargetSelector", () => {
  const snapshot = makeSnapshot();

  it("shows hyperedges for educate verb", () => {
    render(
      <TargetSelector
        snapshot={snapshot}
        verb="educate"
        selectedTarget={null}
        onSelect={vi.fn()}
      />,
    );
    // Educate targets hyperedges (communities)
    // Default fixture includes a hyperedge
    const items = screen.getAllByRole("button");
    expect(items.length).toBeGreaterThan(0);
  });

  it("shows territories for mobilize verb", () => {
    render(
      <TargetSelector
        snapshot={snapshot}
        verb="mobilize"
        selectedTarget={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("Downtown")).toBeInTheDocument();
    expect(screen.getByText("Suburbs")).toBeInTheDocument();
  });

  it("shows organizations for aid verb", () => {
    render(
      <TargetSelector snapshot={snapshot} verb="aid" selectedTarget={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("Workers Union")).toBeInTheDocument();
  });

  it("shows self-targeted message for reproduce verb", () => {
    render(
      <TargetSelector
        snapshot={snapshot}
        verb="reproduce"
        selectedTarget={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/Self-targeted/)).toBeInTheDocument();
  });

  it("fires onSelect with target id on click", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <TargetSelector
        snapshot={snapshot}
        verb="mobilize"
        selectedTarget={null}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByText("Downtown"));
    expect(onSelect).toHaveBeenCalledWith("territory-downtown");
  });

  it("deselects target when clicking the selected target", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <TargetSelector
        snapshot={snapshot}
        verb="mobilize"
        selectedTarget="territory-downtown"
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByText("Downtown"));
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("shows type badges", () => {
    render(
      <TargetSelector
        snapshot={snapshot}
        verb="investigate"
        selectedTarget={null}
        onSelect={vi.fn()}
      />,
    );
    // investigate targets hyperedges, organizations, territories
    const badges = screen.getAllByText(/hyperedge|organization|territory/i);
    expect(badges.length).toBeGreaterThan(0);
  });

  it("shows empty message when no targets", () => {
    const emptySnap = makeSnapshot({
      territories: [],
      organizations: [],
      hyperedges: [],
    });
    render(
      <TargetSelector
        snapshot={emptySnap}
        verb="educate"
        selectedTarget={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/No valid targets/)).toBeInTheDocument();
  });
});
