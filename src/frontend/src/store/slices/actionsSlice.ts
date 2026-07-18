/**
 * Actions slice — the Action Composer's submit path (spec-110 B3 stage 2).
 *
 * Mirrors the legacy `gameStore.submitAction`'s contract exactly: `POST
 * /api/games/{id}/actions/{verb}/` with the verb stripped out of the body
 * (Spec 040 — the verb rides in the URL path, never the payload). The
 * composer builds the body via the ported `VerbConfig.buildPayload`
 * (`@/lib/verbs`) and hands it to `submit` unchanged — this slice never
 * re-derives or re-shapes it, so the wire contract stays byte-identical
 * to the old app's.
 *
 * `pending` is a client-side "submitted against the current tick, not yet
 * resolved" list for Action Composer UI feedback (spec-110 B3's
 * "pending-actions list"). It is cleared by `worldSlice.onTickAdvanced`
 * once the observed tick changes — a resolve consumes every action queued
 * against the prior tick, so the old entries no longer describe reality.
 */

import type { StateCreator } from "zustand";
import { post as apiPost } from "@/api/client";
import type { PlayerVerb } from "@/types/game";
import type { VerbSubmitBody } from "@/lib/verbs";
import type { RootState } from "../types";

export interface PendingActionEntry {
  /** Client-generated id (crypto.randomUUID) — unique within a session. */
  id: string;
  verb: PlayerVerb;
  orgId: string;
  targetId: string | null;
  /** Tick in effect when this action was submitted. */
  submittedAtTick: number;
}

/**
 * A pending composer preset (Track 1 Task 7, 2026-07-18) — set by
 * `presetInvestigate` when a fogged field's card is clicked, consumed once
 * by `ActionComposer` to seed its verb/target selection, never re-applied.
 * INVESTIGATE-only today (the one verb Task 7 needs); a future verb would
 * add its own `presetX` action rather than widen this shape speculatively.
 */
export interface ActionPreset {
  verb: PlayerVerb;
  targetId: string;
  targetLabel: string;
}

export interface ActionsSlice {
  actions: {
    pending: PendingActionEntry[];
    submitting: boolean;
    /** Loud failure message (III.11) — set on a non-ok submit response. */
    error: string | null;
    /** A composer preset awaiting consumption, or `null` — see `ActionPreset`. */
    preset: ActionPreset | null;

    /**
     * POST /api/games/{id}/actions/{verb}/ with `body` verbatim. On success,
     * queues a pending entry and refetches world state (mirrors the legacy
     * `gameStore.submitAction`'s post-submit refetch). Returns whether the
     * submission succeeded.
     */
    submit: (gameId: string, verb: PlayerVerb, body: VerbSubmitBody) => Promise<boolean>;
    /** Drop every queued entry — called on tick advance. */
    clearPending: () => void;
    /** Queue an INVESTIGATE preset naming `targetId` (real graph node id —
     *  `resolve_investigate` reads it directly, with no allow-list against
     *  the (still-mocked, Task 9) target-discovery endpoint) + `targetLabel`
     *  for display. `ActionComposer` consumes it once. */
    presetInvestigate: (targetId: string, targetLabel: string) => void;
    /** Clear the pending preset — called once `ActionComposer` has applied it. */
    consumePreset: () => void;
  };
}

export const createActionsSlice: StateCreator<RootState, [], [], ActionsSlice> = (set, get) => ({
  actions: {
    pending: [],
    submitting: false,
    error: null,
    preset: null,

    submit: async (gameId, verb, body) => {
      set((s) => ({ actions: { ...s.actions, submitting: true, error: null } }));
      const res = await apiPost(`/api/games/${gameId}/actions/${verb}/`, body);

      if (res.status !== "ok") {
        set((s) => ({
          actions: {
            ...s.actions,
            submitting: false,
            error: res.message ?? "Failed to submit action",
          },
        }));
        return false;
      }

      const entry: PendingActionEntry = {
        id: crypto.randomUUID(),
        verb,
        orgId: body.org_id,
        targetId: (body.target_id ?? body.target_community_id ?? null) as string | null,
        submittedAtTick: get().world.snapshot?.tick ?? 0,
      };
      set((s) => ({
        actions: { ...s.actions, submitting: false, pending: [...s.actions.pending, entry] },
      }));
      await get().world.fetchState(gameId);
      return true;
    },

    clearPending: () => set((s) => ({ actions: { ...s.actions, pending: [] } })),

    presetInvestigate: (targetId, targetLabel) =>
      set((s) => ({
        actions: { ...s.actions, preset: { verb: "investigate", targetId, targetLabel } },
      })),

    consumePreset: () => set((s) => ({ actions: { ...s.actions, preset: null } })),
  },
});
