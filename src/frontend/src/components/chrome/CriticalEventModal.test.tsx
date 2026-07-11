/**
 * CriticalEventModal tests — placeholder stub (architecture §4.2's
 * Paradox-style modal for `time.status === "autopaused"`; net-new). Lane E
 * owns the real modal (Open Wire / Resume CTAs reading the autopause
 * event ids); this v1 renders nothing when not autopaused, and an honest
 * minimal surface when it is, so the mount point + testid exist.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CriticalEventModal } from "./CriticalEventModal";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";

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
});
