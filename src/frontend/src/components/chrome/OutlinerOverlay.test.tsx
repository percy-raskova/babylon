/**
 * OutlinerOverlay tests — the collapsible floating left panel hosting the
 * unchanged `Outliner` (architecture §1.2's `shell/Outliner.tsx` →
 * `chrome/OutlinerOverlay.tsx` migrate row; Stellaris outliner idiom).
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OutlinerOverlay } from "./OutlinerOverlay";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("OutlinerOverlay", () => {
  it("hosts the Outliner, which keeps the region-outliner testid", () => {
    render(<OutlinerOverlay gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("region-outliner")).toBeInTheDocument();
  });

  it("collapses via ui.chrome.outlinerOpen, keeping the Outliner mounted but hidden", async () => {
    render(<OutlinerOverlay gameId={DEFAULT_GAME_ID} />);
    expect(useStore.getState().ui.chrome.outlinerOpen).toBe(true);

    await userEvent.click(screen.getByRole("button", { name: /[▾▸]/ }));
    expect(useStore.getState().ui.chrome.outlinerOpen).toBe(false);
    // Still in the DOM (CSS-hidden), never unmounted.
    expect(screen.getByTestId("region-outliner")).toBeInTheDocument();
  });

  it("shrinks to an icon rail when collapsed (Stellaris outliner idiom)", async () => {
    render(<OutlinerOverlay gameId={DEFAULT_GAME_ID} />);
    const panel = screen.getByTestId("outliner-overlay");
    expect(panel).toHaveStyle({ width: "240px" });
    expect(screen.getByText("Outliner")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /[▾▸]/ }));

    expect(panel).toHaveStyle({ width: "44px" });
    expect(screen.getByText("☰")).toBeInTheDocument();
    expect(screen.queryByText("Outliner")).not.toBeInTheDocument();
  });
});
