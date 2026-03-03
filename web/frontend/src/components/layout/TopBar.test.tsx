/**
 * Unit tests for the TopBar component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TopBar } from "./TopBar";
import { makeSnapshot } from "@/test/fixtures";

describe("TopBar", () => {
  const defaultProps = {
    snapshot: makeSnapshot(),
    gameId: "game-001-abcdef",
    username: "testplayer",
    resolving: false,
    onResolve: vi.fn(),
    onBack: vi.fn(),
    onLogout: vi.fn(),
  };

  it("shows tick counter from snapshot", () => {
    render(<TopBar {...defaultProps} />);
    // "1" appears multiple times (tick counter + PersistentIndicators values)
    // Verify tick label and that at least one "1" is the bold tick counter
    expect(screen.getByText("Tick")).toBeInTheDocument();
    const ones = screen.getAllByText("1");
    const tickCounter = ones.find((el) => el.classList.contains("text-2xl"));
    expect(tickCounter).toBeTruthy();
  });

  it("shows truncated game ID", () => {
    render(<TopBar {...defaultProps} />);
    expect(screen.getByText("game-001...")).toBeInTheDocument();
  });

  it("shows username", () => {
    render(<TopBar {...defaultProps} />);
    expect(screen.getByText("testplayer")).toBeInTheDocument();
  });

  it("shows resolve button", () => {
    render(<TopBar {...defaultProps} />);
    expect(screen.getByText("Resolve Tick")).toBeInTheDocument();
  });

  it("disables resolve when resolving", () => {
    render(<TopBar {...defaultProps} resolving={true} />);
    expect(screen.getByText("Resolving...")).toBeDisabled();
  });

  it("back button fires onBack", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<TopBar {...defaultProps} onBack={onBack} />);

    await user.click(screen.getByText(/Games/));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it("logout button fires onLogout", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    render(<TopBar {...defaultProps} onLogout={onLogout} />);

    await user.click(screen.getByText("Logout"));
    expect(onLogout).toHaveBeenCalledOnce();
  });

  it("resolve button fires onResolve", async () => {
    const user = userEvent.setup();
    const onResolve = vi.fn();
    render(<TopBar {...defaultProps} onResolve={onResolve} />);

    await user.click(screen.getByText("Resolve Tick"));
    expect(onResolve).toHaveBeenCalledOnce();
  });
});
