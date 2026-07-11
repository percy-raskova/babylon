/**
 * InspectionStack state (spec-113 §2.3) — skeletal pre-wiring.
 *
 * Owned by Lane C, which replaces the frame internals with resolver-backed
 * fetching (`lib/inspect/resolvers`). This skeleton exists so the slice is
 * registered in the root store before Wave 2 lanes run concurrently
 * (Lane-A stub pattern: shared files pre-wired, lane files owned).
 */

import type { StateCreator } from "zustand";
import type { InspectionNode, InspectionRef } from "@/types/inspection";
import type { RootState } from "../types";

/** One frame in the breadcrumbed inspection stack. */
export interface InspectionFrame {
  ref: InspectionRef;
  data: InspectionNode | null;
  loading: boolean;
  error: string | null;
}

export interface InspectSlice {
  inspect: {
    stack: InspectionFrame[];
    /** Push a child frame for `ref` (resolver fetch is Lane C's work). */
    push: (ref: InspectionRef) => void;
    /** Pop the top frame. */
    pop: () => void;
    /** Pop back to stack index `i` (keeps frames 0..i). */
    popTo: (i: number) => void;
    /** Clear the whole stack. */
    clear: () => void;
  };
}

export const createInspectSlice: StateCreator<RootState, [], [], InspectSlice> = (set) => ({
  inspect: {
    stack: [],
    push: (ref) =>
      set((s) => ({
        inspect: {
          ...s.inspect,
          stack: [...s.inspect.stack, { ref, data: null, loading: false, error: null }],
        },
      })),
    pop: () =>
      set((s) => ({
        inspect: { ...s.inspect, stack: s.inspect.stack.slice(0, -1) },
      })),
    popTo: (i) =>
      set((s) => ({
        inspect: { ...s.inspect, stack: s.inspect.stack.slice(0, i + 1) },
      })),
    clear: () => set((s) => ({ inspect: { ...s.inspect, stack: [] } })),
  },
});
