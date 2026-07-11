/**
 * EventToasts tests — placeholder stub (architecture §4.2/§5.2's transient
 * toast queue; net-new, no legacy component to host). Lane E owns the
 * real toast queue + `eventsSlice`; this v1 renders an honest empty
 * container so the mount point exists for the chrome layer.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EventToasts } from "./EventToasts";

describe("EventToasts", () => {
  it("renders its testid as an empty placeholder container", () => {
    render(<EventToasts gameId="game-1" />);
    const el = screen.getByTestId("event-toasts");
    expect(el).toBeInTheDocument();
    expect(el).toBeEmptyDOMElement();
  });
});
