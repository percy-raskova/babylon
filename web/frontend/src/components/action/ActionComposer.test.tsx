/**
 * Unit tests for the ActionComposer component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ActionComposer } from "./ActionComposer";
import { useUIStore } from "@/stores/uiStore";
import { makeSnapshot } from "@/test/fixtures";

describe("ActionComposer", () => {
  const defaultProps = {
    snapshot: makeSnapshot(),
    onSubmit: vi.fn().mockResolvedValue(undefined),
    onResolve: vi.fn().mockResolvedValue(undefined),
    resolving: false,
  };

  it("renders header and resolve button", () => {
    render(<ActionComposer {...defaultProps} />);
    expect(screen.getByText("Actions")).toBeInTheDocument();
    expect(screen.getByText("Resolve Tick")).toBeInTheDocument();
  });

  it("shows verb grid when org is selected", () => {
    render(<ActionComposer {...defaultProps} />);
    // With organizations in snapshot, first org is auto-selected
    expect(screen.getByText("Select Verb")).toBeInTheDocument();
    expect(screen.getByText("Educate")).toBeInTheDocument();
  });

  it("shows org info pill with budget and cohesion", () => {
    render(<ActionComposer {...defaultProps} />);
    expect(screen.getByText("Workers Union")).toBeInTheDocument();
    expect(screen.getByText(/Budget:/)).toBeInTheDocument();
    expect(screen.getByText(/Cohesion:/)).toBeInTheDocument();
  });

  it("shows empty state when no organizations", () => {
    const emptySnap = makeSnapshot({ organizations: [] });
    render(<ActionComposer {...defaultProps} snapshot={emptySnap} />);
    expect(screen.getByText(/No organizations available/)).toBeInTheDocument();
  });

  it("clicking verb sets pending action in UI store", async () => {
    const user = userEvent.setup();
    render(<ActionComposer {...defaultProps} />);

    await user.click(screen.getByText("Educate"));
    const state = useUIStore.getState();
    expect(state.pendingVerb).toBe("educate");
    expect(state.pendingOrgId).toBe("org-workers-union");
  });

  it("shows target selector after verb selection", async () => {
    const user = userEvent.setup();
    render(<ActionComposer {...defaultProps} />);

    await user.click(screen.getByText("Educate"));
    expect(screen.getByText("Select Target")).toBeInTheDocument();
  });

  it("self-targeted verb skips target and shows preview", async () => {
    const user = userEvent.setup();
    render(<ActionComposer {...defaultProps} />);

    await user.click(screen.getByText("Reproduce"));
    // Should show preview directly (no target selector)
    expect(screen.getByText("Action Preview")).toBeInTheDocument();
    expect(screen.getByText("Submit Action")).toBeInTheDocument();
  });

  it("full flow: verb → target → preview → submit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ActionComposer {...defaultProps} onSubmit={onSubmit} />);

    // Select verb
    await user.click(screen.getByText("Educate"));
    // Select target
    await user.click(screen.getByText("Proletariat"));
    // Preview should appear
    expect(screen.getByText("Action Preview")).toBeInTheDocument();
    // Submit
    await user.click(screen.getByText("Submit Action"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        org_id: "org-workers-union",
        verb: "educate",
        target_id: "entity-proletariat",
      });
    });
  });

  it("cancel clears pending action", async () => {
    const user = userEvent.setup();
    render(<ActionComposer {...defaultProps} />);

    await user.click(screen.getByText("Reproduce"));
    await user.click(screen.getByText("Cancel"));

    const state = useUIStore.getState();
    expect(state.pendingVerb).toBeNull();
    expect(state.pendingOrgId).toBeNull();
  });

  it("resolve button disabled when resolving", () => {
    render(<ActionComposer {...defaultProps} resolving={true} />);
    expect(screen.getByText("Resolving...")).toBeDisabled();
  });
});
