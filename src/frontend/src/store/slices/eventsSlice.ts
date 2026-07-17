/**
 * Event-stream state (spec-113 §4.2, DESIGN_BIBLE §5.2) — the two-stream
 * toast/tray model.
 *
 * Fed by `worldSlice.onTickAdvanced` (one line: `events.ingest(tick,
 * snap.events)`), classified via `lib/eventClassifier.ts`'s
 * `classifyEventsForStream`. Design choices, grounded in DESIGN_BIBLE §5.2:
 *
 * - **Only the urgent stream toasts.** The ambient stream ("the wire feed
 *   is the ambient stream — a newspaper, not a log") never pops a toast;
 *   ambient events still exist on the snapshot for `EventsFeed`/the Wire to
 *   read, this slice just doesn't surface them as interruptions.
 * - **Two toast lifetimes.** `critical` events are individually
 *   persistent-until-acted (each is its own toast — a decision, never
 *   merged). `notable` events from the same tick batch into ONE
 *   ephemeral-with-generous-timing toast ("simultaneous low-priority events
 *   batch into one expandable toast") — the actual generous timeout is a
 *   component-side concern (`EventToasts`); this slice only tags the
 *   lifetime kind and owns no timers itself (matching `orchestrator.ts`'s
 *   heartbeat-owns-timing precedent, not the slices).
 * - **Recoverable dismissal tray.** `dismissToast` moves a toast out of the
 *   active queue into `tray`, never deletes it; `restoreToast` reverses
 *   that ("a missed toast is retrievable, not gone" — HOI4).
 * - **Per-category mute.** Muted categories are filtered out of `ingest`
 *   entirely — never toasted, never trayed (they still reach `EventsFeed`
 *   via the raw snapshot, since muting is a toast/tray-layer courtesy, not
 *   a history redaction).
 */

import type { StateCreator } from "zustand";
import type { RootState } from "../types";
import type { GameEvent } from "@/types/game";
import {
  classifyEventsForStream,
  type EventCategory,
  type StreamEvent,
  type StreamSeverity,
} from "@/lib/eventClassifier";
import { dedupeEvents } from "@/lib/eventDedup";

export type { EventCategory } from "@/lib/eventClassifier";

/**
 * One popped toast: a single critical *condition* (accumulating across
 * ticks by salience key, spec-116 FR-116-2), or a same-tick batch of
 * notable events.
 */
export interface ToastEntry {
  id: string;
  /** Salience identity `${type}:${subject}` for critical toasts; `null` for notable batches. */
  dedupKey: string | null;
  /** Tick of FIRST occurrence. */
  tick: number;
  /** Tick of the most recent occurrence (== tick until the condition persists). */
  lastTick: number;
  /** Raw events this card has absorbed (same-tick repeats + cross-tick recurrences). */
  count: number;
  severity: StreamSeverity;
  /** Persistent-until-acted (critical/decision) vs ephemeral-with-generous-timing (flavor). */
  lifetime: "persistent" | "ephemeral";
  events: StreamEvent[];
}

export interface EventsSlice {
  events: {
    /** Ticks whose events have been ingested (dedup guard). */
    ingestedTicks: number[];
    /** Active toast queue, oldest first. */
    toasts: ToastEntry[];
    /** Dismissed-but-recoverable toasts (HOI4-style tray). */
    tray: ToastEntry[];
    /** Categories the player has muted — filtered out of future toasts/tray. */
    mutedCategories: EventCategory[];

    /** Ingest a tick's raw events: classify, dedup, and enqueue new toasts. */
    ingest: (tick: number, rawEvents: GameEvent[]) => void;
    /** Move an active toast into the recoverable tray. */
    dismissToast: (id: string) => void;
    /** Pull a toast back out of the tray into the active queue. */
    restoreToast: (id: string) => void;
    /** Flip a category's mute state. */
    toggleMuteCategory: (category: EventCategory) => void;
  };
}

export const createEventsSlice: StateCreator<RootState, [], [], EventsSlice> = (set, get) => ({
  events: {
    ingestedTicks: [],
    toasts: [],
    tray: [],
    mutedCategories: [],

    ingest: (tick, rawEvents) => {
      if (get().events.ingestedTicks.includes(tick)) return;

      const muted = new Set(get().events.mutedCategories);
      const classified = classifyEventsForStream(rawEvents).filter(
        (e) => e.stream === "urgent" && !muted.has(e.category),
      );

      // Critical conditions collapse by (type,subject): same-tick repeats
      // into one card, and a condition already toasted — or dismissed into
      // the tray — on an earlier tick ACCUMULATES (count/lastTick) instead
      // of stacking a duplicate (FR-116-2 / acceptance gate 2). A dismissed
      // condition stays dismissed: silent accumulation, never a re-pop.
      const toasts = [...get().events.toasts];
      const tray = [...get().events.tray];
      const fresh: ToastEntry[] = [];
      for (const run of dedupeEvents(classified.filter((e) => e.severity === "critical"))) {
        const bump = (t: ToastEntry): ToastEntry => ({
          ...t,
          count: t.count + run.count,
          lastTick: tick,
          events: run.events,
        });
        const active = toasts.find((t) => t.dedupKey === run.key);
        if (active) {
          toasts[toasts.indexOf(active)] = bump(active);
          continue;
        }
        const trayed = tray.find((t) => t.dedupKey === run.key);
        if (trayed) {
          tray[tray.indexOf(trayed)] = bump(trayed);
          continue;
        }
        fresh.push({
          id: run.representative.id,
          dedupKey: run.key,
          tick,
          lastTick: tick,
          count: run.count,
          severity: "critical" as const,
          lifetime: "persistent" as const,
          events: run.events,
        });
      }

      const notable = classified.filter((e) => e.severity === "notable");
      const batchToast: ToastEntry[] =
        notable.length > 0
          ? [
              {
                id: `batch-${tick}`,
                dedupKey: null,
                tick,
                lastTick: tick,
                count: notable.length,
                severity: "notable" as const,
                lifetime: "ephemeral" as const,
                events: notable,
              },
            ]
          : [];

      set((s) => ({
        events: {
          ...s.events,
          ingestedTicks: [...s.events.ingestedTicks, tick],
          toasts: [...toasts, ...fresh, ...batchToast],
          tray,
        },
      }));
    },

    dismissToast: (id) =>
      set((s) => {
        const toast = s.events.toasts.find((t) => t.id === id);
        if (!toast) return { events: s.events };
        return {
          events: {
            ...s.events,
            toasts: s.events.toasts.filter((t) => t.id !== id),
            tray: [...s.events.tray, toast],
          },
        };
      }),

    restoreToast: (id) =>
      set((s) => {
        const toast = s.events.tray.find((t) => t.id === id);
        if (!toast) return { events: s.events };
        return {
          events: {
            ...s.events,
            tray: s.events.tray.filter((t) => t.id !== id),
            toasts: [...s.events.toasts, toast],
          },
        };
      }),

    toggleMuteCategory: (category) =>
      set((s) => ({
        events: {
          ...s.events,
          mutedCategories: s.events.mutedCategories.includes(category)
            ? s.events.mutedCategories.filter((c) => c !== category)
            : [...s.events.mutedCategories, category],
        },
      })),
  },
});
