/**
 * Event-stream state (spec-113 §4.2) — skeletal pre-wiring.
 *
 * Owned by Lane E, which replaces the internals with the full two-stream
 * model (urgent/ambient), severity classification, toast lifetimes, the
 * recoverable dismissal tray, and per-category mutes (DESIGN_BIBLE §5.2).
 * This skeleton exists so the slice is registered in the root store before
 * Wave 2 lanes run concurrently.
 */

import type { StateCreator } from "zustand";
import type { RootState } from "../types";

export interface EventsSlice {
  events: {
    /** Ticks whose events have been ingested (dedup guard). */
    ingestedTicks: number[];
    /** Ingest a tick's raw event payloads (classification is Lane E's work). */
    ingest: (tick: number, rawEvents: readonly unknown[]) => void;
  };
}

export const createEventsSlice: StateCreator<RootState, [], [], EventsSlice> = (set) => ({
  events: {
    ingestedTicks: [],
    ingest: (tick, _rawEvents) =>
      set((s) =>
        s.events.ingestedTicks.includes(tick)
          ? s
          : {
              events: {
                ...s.events,
                ingestedTicks: [...s.events.ingestedTicks, tick],
              },
            },
      ),
  },
});
