/**
 * Unit tests for the EventLog component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EventLog } from "./EventLog";
import { makeSnapshot, makeEvent } from "@/test/fixtures";

describe("EventLog", () => {
  it("shows empty state when no events", () => {
    const snap = makeSnapshot({ events: [] });
    render(<EventLog snapshot={snap} />);
    expect(screen.getByText(/No events recorded/)).toBeInTheDocument();
  });

  it("renders events with type labels", () => {
    const snap = makeSnapshot({
      events: [
        makeEvent({ type: "EXTRACTION", tick: 1 }),
        makeEvent({ type: "UPRISING", tick: 1, data: { message: "revolt" } }),
      ],
    });
    render(<EventLog snapshot={snap} />);
    expect(screen.getByText("EXTRACTION")).toBeInTheDocument();
    expect(screen.getByText("UPRISING")).toBeInTheDocument();
  });

  it("shows event icons", () => {
    const snap = makeSnapshot({
      events: [makeEvent({ type: "UPRISING", tick: 1 })],
    });
    render(<EventLog snapshot={snap} />);
    expect(screen.getByText("!!")).toBeInTheDocument();
  });

  it("shows tick number", () => {
    const snap = makeSnapshot({
      events: [makeEvent({ tick: 5 })],
    });
    render(<EventLog snapshot={snap} />);
    expect(screen.getByText("T5")).toBeInTheDocument();
  });

  it("formats event message from data fields", () => {
    const snap = makeSnapshot({
      events: [
        makeEvent({
          type: "VALUE_TRANSFER",
          data: { source: "core", target: "periphery", amount: 12.5 },
        }),
      ],
    });
    render(<EventLog snapshot={snap} />);
    expect(screen.getByText(/from:core/)).toBeInTheDocument();
    expect(screen.getByText(/to:periphery/)).toBeInTheDocument();
  });

  it("renders multiple events", () => {
    const events = Array.from({ length: 5 }, (_, i) =>
      makeEvent({ type: `EVENT_${i}`, tick: i + 1 }),
    );
    const snap = makeSnapshot({ events });
    render(<EventLog snapshot={snap} />);
    expect(screen.getByText("T1")).toBeInTheDocument();
    expect(screen.getByText("T5")).toBeInTheDocument();
  });
});
