/**
 * Integration test: event log with snapshot events.
 *
 * Tests that events from the snapshot render correctly in EventLog.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EventLog } from "@/components/events/EventLog";
import { makeSnapshot, makeEvent } from "@/test/fixtures";

describe("event log flow", () => {
  it("renders events from snapshot", () => {
    const snapshot = makeSnapshot({
      events: [
        makeEvent({
          type: "UPRISING",
          tick: 3,
          data: { entity_id: "entity-proletariat", message: "Workers rose up" },
        }),
        makeEvent({
          type: "EXCESSIVE_FORCE",
          tick: 3,
          data: { territory_id: "territory-downtown", message: "State forces deployed" },
        }),
      ],
    });

    render(<EventLog snapshot={snapshot} />);

    // Event types should be displayed
    expect(screen.getByText("UPRISING")).toBeInTheDocument();
    expect(screen.getByText("EXCESSIVE_FORCE")).toBeInTheDocument();
    // Tick numbers
    expect(screen.getAllByText("T3")).toHaveLength(2);
  });

  it("shows empty state when no events", () => {
    const snapshot = makeSnapshot({ events: [] });
    render(<EventLog snapshot={snapshot} />);
    expect(screen.getByText("No events recorded yet")).toBeInTheDocument();
  });

  it("formats event data into message", () => {
    const snapshot = makeSnapshot({
      events: [
        makeEvent({
          type: "EXTRACTION",
          data: { source_id: "entity-bourgeoisie", amount: 10.5 },
        }),
      ],
    });

    render(<EventLog snapshot={snapshot} />);
    expect(screen.getByText("EXTRACTION")).toBeInTheDocument();
    // formatEventMessage should show source_id and amount
    expect(screen.getByText(/from:entity-bourgeoisie/)).toBeInTheDocument();
  });
});
