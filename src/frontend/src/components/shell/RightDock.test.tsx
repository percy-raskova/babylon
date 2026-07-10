import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RightDock } from "./RightDock";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("RightDock", () => {
  it("defaults to the Actions tab", () => {
    render(<RightDock gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("action-composer")).toBeInTheDocument();
  });

  it("switches to the Inspector tab", async () => {
    render(<RightDock gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByRole("button", { name: "Inspector" }));
    expect(screen.getByTestId("inspector-empty")).toBeInTheDocument();
    expect(useStore.getState().ui.rightDockTab).toBe("inspector");
  });
});
