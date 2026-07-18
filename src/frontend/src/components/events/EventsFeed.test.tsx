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
      time: { ...s.time, autopauseEventKeys: ["rupture:territory-downtown"] },
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
          events: [
            makeEvent({
              id: "e1",
              type: "endgame_reached",
              title: "The Horizon",
              tick: 3,
              data: {},
            }),
          ],
        }),
      },
      time: { ...s.time, autopauseEventKeys: ["endgame_reached:global"] },
    }));
    render(<EventsFeed />);

    const button = screen.getByText("The Horizon").closest("button");
    expect(button).not.toBeDisabled();
    await userEvent.click(screen.getByText("The Horizon"));
    expect(useStore.getState().ui.takeover.active).toBe("chronicle");
  });

  it("collapses consecutive same-(type,subject) events into one card with count and age (FR-116-2)", () => {
    useStore.setState((s) => ({
      world: {
        ...s.world,
        snapshot: makeSnapshot({
          events: [
            makeEvent({
              id: "e1",
              type: "dispossession_event",
              title: "Dispossession",
              tick: 5,
              data: { territory: "26163" },
            }),
            makeEvent({
              id: "e2",
              type: "dispossession_event",
              title: "Dispossession",
              tick: 5,
              data: { territory: "26163" },
            }),
            makeEvent({
              id: "e3",
              type: "dispossession_event",
              title: "Dispossession",
              tick: 5,
              data: { territory: "26099" },
            }),
          ],
        }),
      },
    }));
    render(<EventsFeed />);

    // The 26163 run collapses into one card; 26099 stays separate.
    expect(screen.getAllByText("Dispossession")).toHaveLength(2);
    expect(screen.getByTestId("event-count-5-0")).toHaveTextContent("×2");
    expect(screen.queryByTestId("event-count-5-2")).not.toBeInTheDocument();
    // Age label (per-tick feed: single tick).
    expect(screen.getAllByText("t5")).toHaveLength(2);

    // The card exposes its `${type}:${subject}` dedup key as data-dedup-key —
    // the affordance the first-session gate-2 e2e asserts adjacency on. These
    // two ADJACENT dispossession cards (26163 collapsed, 26099 separate) carry
    // the SAME type but DIFFERENT keys: exactly the case a type-only adjacency
    // check would false-fail, and the reason gate 2 must key on (type,subject).
    const key26163 = screen.getByTestId("event-5-0").getAttribute("data-dedup-key");
    const key26099 = screen.getByTestId("event-5-2").getAttribute("data-dedup-key");
    expect(key26163).toMatch(/^dispossession_event:/);
    expect(key26099).toMatch(/^dispossession_event:/);
    expect(key26163).not.toBe(key26099);
  });
});
