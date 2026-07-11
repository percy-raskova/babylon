/**
 * SpeedControls tests — the real speed cluster (architecture §4.1,
 * DESIGN_BIBLE §5.1/§5.3). Keeps `time-status`/`time-controls`/
 * `time-resume` (TimeControls' contract) and adds `speed-1`/`speed-2`/
 * `speed-5`.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SpeedControls } from "./SpeedControls";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("SpeedControls", () => {
  it("keeps the legacy TimeControls testids (time-controls, time-status)", () => {
    render(<SpeedControls gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("time-controls")).toBeInTheDocument();
    expect(screen.getByTestId("time-status")).toHaveTextContent("PAUSED");
  });

  it("renders the three speed buttons with speed-1/speed-2/speed-5 testids", () => {
    render(<SpeedControls gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("speed-1")).toBeInTheDocument();
    expect(screen.getByTestId("speed-2")).toBeInTheDocument();
    expect(screen.getByTestId("speed-5")).toBeInTheDocument();
  });

  it("defaults to speed 5 marked aria-pressed", () => {
    render(<SpeedControls gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("speed-5")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("speed-1")).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking speed-1 calls time.setSpeed(1)", async () => {
    render(<SpeedControls gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByTestId("speed-1"));

    expect(useStore.getState().time.speed).toBe(1);
    expect(screen.getByTestId("speed-1")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("speed-5")).toHaveAttribute("aria-pressed", "false");
  });

  it("speed buttons stay live mid-resolve (not disabled)", () => {
    useStore.setState((s) => ({ time: { ...s.time, status: "resolving" } }));
    render(<SpeedControls gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("speed-1")).not.toBeDisabled();
  });

  it("number keys 1/2/3 set speed via the component's own shortcut hook", async () => {
    render(<SpeedControls gameId={DEFAULT_GAME_ID} />);
    const user = userEvent.setup();

    await user.keyboard("1");
    expect(useStore.getState().time.speed).toBe(1);

    await user.keyboard("2");
    expect(useStore.getState().time.speed).toBe(2);

    await user.keyboard("3");
    expect(useStore.getState().time.speed).toBe(5);
  });

  it("ignores number-key shortcuts while focus is in a text input", async () => {
    render(
      <div>
        <input data-testid="some-input" />
        <SpeedControls gameId={DEFAULT_GAME_ID} />
      </div>,
    );
    useStore.getState().time.setSpeed(5);
    const input = screen.getByTestId("some-input");
    input.focus();

    await userEvent.keyboard("1");

    expect(useStore.getState().time.speed).toBe(5);
  });
});
