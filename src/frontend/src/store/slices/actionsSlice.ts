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

export interface ActionsSlice {
  actions: {
    pending: PendingActionEntry[];
    submitting: boolean;
    /** Loud failure message (III.11) — set on a non-ok submit response. */
    error: string | null;

    /**
     * POST /api/games/{id}/actions/{verb}/ with `body` verbatim. On success,
     * queues a pending entry and refetches world state (mirrors the legacy
     * `gameStore.submitAction`'s post-submit refetch). Returns whether the
     * submission succeeded.
     */
    submit: (gameId: string, verb: PlayerVerb, body: VerbSubmitBody) => Promise<boolean>;
    /** Drop every queued entry — called on tick advance. */
    clearPending: () => void;
  };
}

export const createActionsSlice: StateCreator<RootState, [], [], ActionsSlice> = (set, get) => ({
  actions: {
    pending: [],
    submitting: false,
    error: null,

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
  },
});
