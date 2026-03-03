/**
 * Integration test: full action submission flow.
 *
 * Tests the ActionComposer → API → store → re-render cycle.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ActionComposer } from "@/components/action/ActionComposer";
import { useUIStore } from "@/stores/uiStore";
import { makeSnapshot } from "@/test/fixtures";

describe("action submission flow", () => {
  const snapshot = makeSnapshot();

  it("completes full verb → target → submit cycle", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ActionComposer
        snapshot={snapshot}
        onSubmit={onSubmit}
        onResolve={vi.fn()}
        resolving={false}
      />,
    );

    // Step 1: Org is auto-selected (only 1 org). Select verb "Educate"
    await user.click(screen.getByText("Educate"));

    // Step 2: Target selector appears — select an entity
    await waitFor(() => {
      expect(screen.getByText("Select Target")).toBeInTheDocument();
    });

    // The TargetSelector shows entities by name — click "Proletariat"
    await user.click(screen.getByText("Proletariat"));

    // Step 3: Preview should show with Submit button
    await waitFor(() => {
      expect(screen.getByText("Submit Action")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Submit Action"));

    // Verify submission
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce();
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          verb: "educate",
          org_id: "org-workers-union",
        }),
      );
    });
  });

  it("self-targeted verb (reproduce) skips target selection", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ActionComposer
        snapshot={snapshot}
        onSubmit={onSubmit}
        onResolve={vi.fn()}
        resolving={false}
      />,
    );

    // Select "Reproduce" which is SELF_TARGETED
    await user.click(screen.getByText("Reproduce"));

    // Should skip target and go straight to preview
    await waitFor(() => {
      expect(screen.getByText("Submit Action")).toBeInTheDocument();
    });
  });

  it("cancel clears pending action in UI store", async () => {
    const user = userEvent.setup();

    render(
      <ActionComposer
        snapshot={snapshot}
        onSubmit={vi.fn()}
        onResolve={vi.fn()}
        resolving={false}
      />,
    );

    // Select Reproduce (self-targeted) to get to preview
    await user.click(screen.getByText("Reproduce"));
    await waitFor(() => {
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Cancel"));

    // Should clear pending action in UI store
    expect(useUIStore.getState().pendingVerb).toBeNull();
  });

  it("submit clears pending state after completion", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ActionComposer
        snapshot={snapshot}
        onSubmit={onSubmit}
        onResolve={vi.fn()}
        resolving={false}
      />,
    );

    // Select Reproduce → preview → submit
    await user.click(screen.getByText("Reproduce"));
    await waitFor(() => {
      expect(screen.getByText("Submit Action")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Submit Action"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce();
    });

    // Pending state should be cleared
    await waitFor(() => {
      expect(useUIStore.getState().pendingVerb).toBeNull();
    });
  });
});
