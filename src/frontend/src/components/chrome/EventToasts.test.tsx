/**
 * EventToasts tests — the toast queue (architecture §4.2/§5.2). Two
 * lifetimes (persistent-until-acted for critical, ephemeral for batched
 * notable events), dismiss -> recoverable tray, per-category mute.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventToasts } from "./EventToasts";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { makeEvent } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
});

describe("EventToasts", () => {
  it("renders its testid as an empty placeholder container when there are no toasts", () => {
    render(<EventToasts gameId="game-1" />);
    const el = screen.getByTestId("event-toasts");
    expect(el).toBeInTheDocument();
    expect(el).toBeEmptyDOMElement();
  });

  it("renders one persistent toast per critical event, with Open Wire + Dismiss CTAs", () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
    render(<EventToasts gameId="game-1" />);

    const id = useStore.getState().events.toasts[0]!.id;
    expect(screen.getByTestId(`toast-${id}`)).toBeInTheDocument();
    expect(screen.getByTestId(`toast-open-wire-${id}`)).toBeInTheDocument();
    expect(screen.getByTestId(`toast-dismiss-${id}`)).toBeInTheDocument();
  });

  it("batches same-tick notable events into one expandable toast", async () => {
    useStore
      .getState()
      .events.ingest(2, [
        makeEvent({ type: "uprising", tick: 2, id: "e1" }),
        makeEvent({ type: "excessive_force", tick: 2, id: "e2" }),
      ]);
    render(<EventToasts gameId="game-1" />);

    const id = useStore.getState().events.toasts[0]!.id;
    expect(screen.getByTestId(`toast-expand-${id}`)).toHaveTextContent("2 developments this tick");

    await userEvent.click(screen.getByTestId(`toast-expand-${id}`));
    expect(screen.queryByTestId(`toast-expand-${id}`)).not.toBeInTheDocument();
  });

  it("Dismiss moves the toast into the recoverable tray, not away entirely", async () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
    render(<EventToasts gameId="game-1" />);

    const id = useStore.getState().events.toasts[0]!.id;
    await userEvent.click(screen.getByTestId(`toast-dismiss-${id}`));

    expect(useStore.getState().events.toasts).toHaveLength(0);
    expect(useStore.getState().events.tray).toHaveLength(1);
  });

  it("Open Wire opens the wire takeover", async () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
    render(<EventToasts gameId="game-1" />);

    const id = useStore.getState().events.toasts[0]!.id;
    await userEvent.click(screen.getByTestId(`toast-open-wire-${id}`));

    expect(useStore.getState().ui.takeover.active).toBe("wire");
  });

  it("mute button on a toast mutes that category for future ingests", async () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
    render(<EventToasts gameId="game-1" />);

    const id = useStore.getState().events.toasts[0]!.id;
    await userEvent.click(screen.getByTestId(`toast-mute-${id}-struggle`));

    expect(useStore.getState().events.mutedCategories).toContain("struggle");
  });

  it("auto-dismisses an ephemeral (batched notable) toast after the generous timeout", async () => {
    vi.useFakeTimers();
    try {
      useStore.getState().events.ingest(2, [makeEvent({ type: "uprising", tick: 2, id: "e1" })]);
      render(<EventToasts gameId="game-1" />);

      expect(useStore.getState().events.toasts).toHaveLength(1);
      await vi.advanceTimersByTimeAsync(12000);

      expect(useStore.getState().events.toasts).toHaveLength(0);
      expect(useStore.getState().events.tray).toHaveLength(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("does NOT auto-dismiss a persistent (critical) toast", async () => {
    vi.useFakeTimers();
    try {
      useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
      render(<EventToasts gameId="game-1" />);

      await vi.advanceTimersByTimeAsync(60000);

      expect(useStore.getState().events.toasts).toHaveLength(1);
    } finally {
      vi.useRealTimers();
    }
  });
});
