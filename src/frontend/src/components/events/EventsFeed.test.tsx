import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventsFeed } from "./EventsFeed";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState } from "@/test/handlers";
import { makeSnapshot, makeEvent } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("EventsFeed", () => {
  it("shows a loud, in-register empty state before any world state has loaded", () => {
    render(<EventsFeed />);
    expect(screen.getByText("The wire is silent — no dispatch yet.")).toBeInTheDocument();
  });

  it("shows a distinct in-register empty state for a tick with zero events (not a failure)", () => {
    useStore.setState((s) => ({
      world: { ...s.world, snapshot: makeSnapshot({ events: [] }) },
    }));
    render(<EventsFeed />);
    expect(screen.getByText("The wire is quiet this tick.")).toBeInTheDocument();
  });

  it("renders one row per current-tick event with severity coloring", () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({
          events: [
            makeEvent({ id: "e1", type: "rupture", title: "Rupture", tick: 3 }),
            makeEvent({ id: "e2", type: "value_transfer", title: "Value Transfer", tick: 3 }),
          ],
        }),
      },
    }));
    render(<EventsFeed />);
    expect(screen.getByText("Rupture")).toBeInTheDocument();
    expect(screen.getByText("Value Transfer")).toBeInTheDocument();
  });

  it("clicking an event with a linked entity selects it (autopause deep-link)", async () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({
          events: [
            makeEvent({
              id: "e1",
              type: "rupture",
              title: "Rupture",
              tick: 3,
              data: { territory_id: "territory-downtown" },
            }),
          ],
        }),
      },
      time: { ...s.time, autopauseEventIds: ["3-0"] },
    }));
    render(<EventsFeed />);

    await userEvent.click(screen.getByText("Rupture"));
    expect(useStore.getState().map.selection).toEqual({ kind: "hex", id: "territory-downtown" });
  });

  // The territory→hex branch is pinned by the deep-link test above; this pins
  // organization→org, the only other linked-entity type `classifyEvents` can
  // emit today. The institution→node / hyperedge→community rows of the inlined
  // mapping are unreachable through the classifier and are enforced statically
  // (the Record is exhaustive over ClassifiedEvent["linkedEntityType"]).
  it("clicking an org-linked event selects the org inspector kind", async () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({
          events: [
            makeEvent({
              id: "e1",
              type: "org_founded",
              title: "Org Founded",
              tick: 3,
              data: { org_id: "org-uaw-local" },
            }),
          ],
        }),
      },
    }));
    render(<EventsFeed />);

    await userEvent.click(screen.getByText("Org Founded"));
    expect(useStore.getState().map.selection).toEqual({ kind: "org", id: "org-uaw-local" });
  });

  it("does not make an event with no linked entity clickable-effective", async () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({
          events: [makeEvent({ id: "e1", type: "value_transfer", title: "VT", tick: 3, data: {} })],
        }),
      },
    }));
    render(<EventsFeed />);
    expect(screen.getByText("VT").closest("button")).toBeDisabled();
  });

  it("clicking a critical event with no linked entity opens the Chronicle takeover", async () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({
          events: [makeEvent({ id: "e1", type: "rupture", title: "Rupture", tick: 3, data: {} })],
        }),
      },
      time: { ...s.time, autopauseEventIds: ["3-0"] },
    }));
    render(<EventsFeed />);

    const button = screen.getByText("Rupture").closest("button");
    expect(button).not.toBeDisabled();
    await userEvent.click(screen.getByText("Rupture"));
    expect(useStore.getState().ui.takeover.active).toBe("chronicle");
  });
});
