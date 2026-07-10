import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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

  it("switches to the Objectives tab and renders objectives from the panel (spec-110 B5)", async () => {
    render(<RightDock gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByRole("button", { name: "Objectives" }));
    expect(useStore.getState().ui.rightDockTab).toBe("objectives");
    await waitFor(() => expect(screen.getByText("Revolutionary Victory")).toBeInTheDocument());
  });

  it("mounts/unmounts the objectives panel only while its tab is active", async () => {
    render(<RightDock gameId={DEFAULT_GAME_ID} />);
    expect(useStore.getState().panels.objectives.mounted).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Objectives" }));
    await waitFor(() => expect(useStore.getState().panels.objectives.mounted).toBe(true));
    await userEvent.click(screen.getByRole("button", { name: "Actions" }));
    expect(useStore.getState().panels.objectives.mounted).toBe(false);
  });
});
