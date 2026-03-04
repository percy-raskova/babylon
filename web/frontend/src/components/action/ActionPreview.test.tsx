/**
 * Unit tests for the ActionPreview component.
 *
 * ActionPreview now fetches from the preview API on mount using useParams
 * for game ID. The submit button is disabled while loading.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ActionPreview } from "./ActionPreview";

/** Wrap ActionPreview in a MemoryRouter with a game/:id route for useParams. */
function renderWithRouter(props: React.ComponentProps<typeof ActionPreview>) {
  return render(
    <MemoryRouter initialEntries={["/game/game-001"]}>
      <Routes>
        <Route path="/game/:id" element={<ActionPreview {...props} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ActionPreview", () => {
  const defaultProps = {
    verb: "educate" as const,
    orgId: "org-workers-union",
    targetId: "entity-proletariat",
    submitting: false,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  };

  it("shows verb label", () => {
    renderWithRouter(defaultProps);
    expect(screen.getByText("Educate")).toBeInTheDocument();
  });

  it("shows organization ID", () => {
    renderWithRouter(defaultProps);
    expect(screen.getByText("org-workers-union")).toBeInTheDocument();
  });

  it("shows target ID when present", () => {
    renderWithRouter(defaultProps);
    expect(screen.getByText("entity-proletariat")).toBeInTheDocument();
  });

  it("hides target when null", () => {
    renderWithRouter({ ...defaultProps, targetId: null });
    expect(screen.queryByText("Target")).not.toBeInTheDocument();
  });

  it("submit button fires onSubmit after loading completes", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithRouter({ ...defaultProps, onSubmit });

    // Wait for loading to complete (preview fetch via MSW)
    await waitFor(() => {
      expect(screen.getByText("Submit Action")).not.toBeDisabled();
    });

    await user.click(screen.getByText("Submit Action"));
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it("cancel button fires onCancel", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    renderWithRouter({ ...defaultProps, onCancel });

    await user.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("disables buttons when submitting", () => {
    renderWithRouter({ ...defaultProps, submitting: true });
    expect(screen.getByText("Submitting...")).toBeDisabled();
    expect(screen.getByText("Cancel")).toBeDisabled();
  });
});
