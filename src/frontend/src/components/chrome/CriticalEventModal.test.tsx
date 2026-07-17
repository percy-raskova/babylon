/**
 * CriticalEventModal tests — the Paradox-style modal for
 * `time.status === "autopaused"` (architecture §4.2): lists the firing
 * events and offers "Open Wire" / "Resume" CTAs.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CriticalEventModal } from "./CriticalEventModal";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { makeEvent, makeSnapshot } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
});

describe("CriticalEventModal", () => {
  it("renders nothing when time.status is not autopaused", () => {
    render(<CriticalEventModal gameId="game-1" />);
    expect(screen.queryByTestId("critical-event-modal")).not.toBeInTheDocument();
  });

  it("renders when time.status is autopaused", () => {
    useStore.setState((s) => ({ time: { ...s.time, status: "autopaused" } }));
    render(<CriticalEventModal gameId="game-1" />);
    expect(screen.getByTestId("critical-event-modal")).toBeInTheDocument();
  });

  it("lists the firing conditions resolved from time.autopauseEventKeys against the current tick", () => {
    const rupture = makeEvent({ type: "rupture", tick: 3, id: "rupture-id", data: {} });
    useStore.setState((s) => ({
      time: { ...s.time, status: "autopaused", autopauseEventKeys: ["rupture:global"] },
      world: { ...s.world, snapshot: makeSnapshot({ tick: 3, events: [rupture] }) },
    }));

    render(<CriticalEventModal gameId="game-1" />);

    expect(screen.getByTestId("autopause-event-rupture:global")).toBeInTheDocument();
    expect(screen.getByTestId("autopause-event-rupture:global")).toHaveTextContent(rupture.title);
  });

  it("collapses same-key repeats into one firing card with a count (FR-116-2)", () => {
    useStore.setState((s) => ({
      time: { ...s.time, status: "autopaused", autopauseEventKeys: ["rupture:global"] },
      world: {
        ...s.world,
        snapshot: makeSnapshot({
          tick: 3,
          events: [
            makeEvent({ type: "rupture", tick: 3, id: "r1", data: {} }),
            makeEvent({ type: "rupture", tick: 3, id: "r2", data: {} }),
          ],
        }),
      },
    }));

    render(<CriticalEventModal gameId="game-1" />);

    expect(screen.getAllByTestId("autopause-event-rupture:global")).toHaveLength(1);
    expect(screen.getByTestId("autopause-event-rupture:global")).toHaveTextContent("×2");
  });

  it("Open Wire opens the wire takeover", async () => {
    useStore.setState((s) => ({ time: { ...s.time, status: "autopaused" } }));
    render(<CriticalEventModal gameId="game-1" />);

    await userEvent.click(screen.getByTestId("autopause-open-wire"));

    expect(useStore.getState().ui.takeover.active).toBe("wire");
  });

  it("Resume clears the autopaused status back to paused", async () => {
    useStore.setState((s) => ({
      time: { ...s.time, status: "autopaused", autopauseEventKeys: ["e1"] },
    }));
    render(<CriticalEventModal gameId="game-1" />);

    await userEvent.click(screen.getByTestId("autopause-resume"));

    expect(useStore.getState().time.status).toBe("paused");
    expect(screen.queryByTestId("critical-event-modal")).not.toBeInTheDocument();
  });
});
