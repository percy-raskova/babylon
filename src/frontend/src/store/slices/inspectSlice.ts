/**
 * InspectionStack state (spec-113 §2.3, DESIGN_BIBLE.md §4) — fleshed out
 * in place from Wave 1's skeleton (Lane C).
 *
 * Each frame owns `{ref, data, loading, error}` per the frozen skeleton,
 * plus two Lane-C-local fields used only inside this file/`InspectionStack`:
 * `pinned` (Escape/backdrop-driven `pop()` skips a pinned top frame — the
 * bible's "pin keeps a frame open"; `popTo`/`clear` are deliberate
 * navigation, not implicit dismissal, so they are NOT pin-gated) and
 * `fetchedAtTick` (drives "cache by refKey(ref) per tick": a frame is not
 * refetched merely by re-rendering or by becoming visible again unless
 * the world tick has moved past its last fetch).
 *
 * Tick fan-out: `worldSlice` (Lane E's file, out of this lane's ownership)
 * has no InspectionStack hook point, so this slice registers its own
 * store subscription at creation time (the "subscribe pattern from your
 * own files" the lane brief calls for) — on every `world.snapshot.tick`
 * change, only the TOP frame refetches; lower frames simply carry a stale
 * `fetchedAtTick` and refetch lazily the moment `pop`/`popTo` makes them
 * the top frame again (architecture.md §2.3).
 */

import type { StateCreator } from "zustand";
import type { InspectionNode, InspectionRef } from "@/types/inspection";
import type { RootState } from "../types";
import { resolveRef, refKey } from "@/lib/inspect/resolvers";

/** DESIGN_BIBLE.md §4: "depth is content-limited, not technically infinite" — hard cap. */
export const MAX_INSPECTION_DEPTH = 6;

/** One frame in the breadcrumbed inspection stack. */
export interface InspectionFrame {
  ref: InspectionRef;
  data: InspectionNode | null;
  loading: boolean;
  error: string | null;
  pinned: boolean;
  fetchedAtTick: number | null;
}

export interface InspectSlice {
  inspect: {
    stack: InspectionFrame[];
    /** Push a child frame for `ref` and resolve it. No-ops past `MAX_INSPECTION_DEPTH`. */
    push: (ref: InspectionRef) => void;
    /** Pop the top frame — a no-op when the top frame is `pinned` (implicit/Escape dismissal only). */
    pop: () => void;
    /** Pop back to stack index `i` (keeps frames 0..i); refetches the revealed top frame if stale. */
    popTo: (i: number) => void;
    /** Clear the whole stack. */
    clear: () => void;
    /** Flip `pinned` on the frame at `index`. */
    togglePin: (index: number) => void;
  };
}

function freshFrame(ref: InspectionRef): InspectionFrame {
  return { ref, data: null, loading: true, error: null, pinned: false, fetchedAtTick: null };
}

export const createInspectSlice: StateCreator<RootState, [], [], InspectSlice> = (
  set,
  get,
  api,
) => {
  const setFrame = (index: number, updater: (f: InspectionFrame) => InspectionFrame): void => {
    set((s) => ({
      inspect: {
        ...s.inspect,
        stack: s.inspect.stack.map((f, i) => (i === index ? updater(f) : f)),
      },
    }));
  };

  /** Fetch `ref`'s node into the frame at `index` — guarded by refKey so a
   * stale (superseded) response can never clobber a newer frame occupying
   * the same index (mirrors the legacy inspectorPanel's `selectionKey` guard). */
  const fetchFrame = async (index: number, ref: InspectionRef): Promise<void> => {
    const gameId = get().session.activeGameId;
    const tick = get().world.snapshot?.tick ?? null;
    const stillCurrent = (): boolean =>
      refKey(get().inspect.stack[index]?.ref ?? ref) === refKey(ref);

    if (!gameId) {
      if (stillCurrent()) {
        setFrame(index, (f) => ({
          ...f,
          data: null,
          loading: false,
          error: "No active game",
          fetchedAtTick: tick,
        }));
      }
      return;
    }

    if (stillCurrent()) {
      setFrame(index, (f) => ({ ...f, loading: true, error: null }));
    }

    try {
      const node: InspectionNode = await resolveRef(gameId, ref);
      if (stillCurrent()) {
        setFrame(index, (f) => ({
          ...f,
          data: node,
          loading: false,
          error: null,
          fetchedAtTick: tick,
        }));
      }
    } catch (err) {
      if (stillCurrent()) {
        setFrame(index, (f) => ({
          ...f,
          loading: false,
          error: err instanceof Error ? err.message : "Failed to load",
          fetchedAtTick: tick,
        }));
      }
    }
  };

  /** Refetch the frame at `index` only if it isn't already loading and its cached tick is stale. */
  const refocus = (index: number): void => {
    const frame = get().inspect.stack[index];
    const tick = get().world.snapshot?.tick ?? null;
    if (frame && !frame.loading && frame.fetchedAtTick !== tick) {
      void fetchFrame(index, frame.ref);
    }
  };

  api.subscribe((state, prevState) => {
    const tick = state.world.snapshot?.tick ?? null;
    if (tick === (prevState.world.snapshot?.tick ?? null)) return;
    const topIndex = state.inspect.stack.length - 1;
    const top = state.inspect.stack[topIndex];
    if (top && top.fetchedAtTick !== tick) {
      void fetchFrame(topIndex, top.ref);
    }
  });

  return {
    inspect: {
      stack: [],

      push: (ref) => {
        set((s) => {
          if (s.inspect.stack.length >= MAX_INSPECTION_DEPTH) return s;
          return { inspect: { ...s.inspect, stack: [...s.inspect.stack, freshFrame(ref)] } };
        });
        const idx = get().inspect.stack.length - 1;
        const top = get().inspect.stack[idx];
        if (top && refKey(top.ref) === refKey(ref)) {
          void fetchFrame(idx, ref);
        }
      },

      pop: () => {
        const stack = get().inspect.stack;
        if (stack[stack.length - 1]?.pinned) return;
        set((s) => ({ inspect: { ...s.inspect, stack: s.inspect.stack.slice(0, -1) } }));
        refocus(get().inspect.stack.length - 1);
      },

      popTo: (i) => {
        set((s) => ({ inspect: { ...s.inspect, stack: s.inspect.stack.slice(0, i + 1) } }));
        refocus(get().inspect.stack.length - 1);
      },

      clear: () => set((s) => ({ inspect: { ...s.inspect, stack: [] } })),

      togglePin: (index) =>
        set((s) => ({
          inspect: {
            ...s.inspect,
            stack: s.inspect.stack.map((f, i) => (i === index ? { ...f, pinned: !f.pinned } : f)),
          },
        })),
    },
  };
};
