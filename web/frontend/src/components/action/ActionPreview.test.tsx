/**
 * Unit tests for the ActionPreview component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ActionPreview } from "./ActionPreview";

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
    render(<ActionPreview {...defaultProps} />);
    expect(screen.getByText("Educate")).toBeInTheDocument();
  });

  it("shows organization ID", () => {
    render(<ActionPreview {...defaultProps} />);
    expect(screen.getByText("org-workers-union")).toBeInTheDocument();
  });

  it("shows target ID when present", () => {
    render(<ActionPreview {...defaultProps} />);
    expect(screen.getByText("entity-proletariat")).toBeInTheDocument();
  });

  it("hides target when null", () => {
    render(<ActionPreview {...defaultProps} targetId={null} />);
    expect(screen.queryByText("Target")).not.toBeInTheDocument();
  });

  it("submit button fires onSubmit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ActionPreview {...defaultProps} onSubmit={onSubmit} />);

    await user.click(screen.getByText("Submit Action"));
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it("cancel button fires onCancel", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<ActionPreview {...defaultProps} onCancel={onCancel} />);

    await user.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("disables buttons when submitting", () => {
    render(<ActionPreview {...defaultProps} submitting={true} />);
    expect(screen.getByText("Submitting...")).toBeDisabled();
    expect(screen.getByText("Cancel")).toBeDisabled();
  });
});
