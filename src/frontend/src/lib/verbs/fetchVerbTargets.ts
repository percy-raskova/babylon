/**
 * fetchVerbTargets — live per-verb target fetch, store-free.
 *
 * Extracted from `web/frontend/src/stores/gameStore.ts`'s
 * `fetchVerbTargets` zustand action (spec-110 B2 port): this module keeps
 * the pure fetch-and-normalize behavior (the actual network call, and the
 * envelope-unwrapping quirk below) without the zustand cache/state
 * mutation, which belongs to whichever store wraps this in B3.
 *
 * Verb target endpoints return flat responses (targets, cost, etc. at the
 * top level) rather than using the standard {status, data} envelope. Some
 * (mobilize) have no status field at all, so `res.status` is `undefined` on
 * success — `api/client`'s `get()` only synthesizes `status: "error"` on
 * failures, so we key off that rather than assuming a shape.
 */

import { get as apiGet } from "@/api/client";
import type { PlayerVerb } from "@/types/game";

export interface VerbTargetsResult {
  /** False when the request failed (network error or HTTP/API error). */
  ok: boolean;
  /** The flat target payload (empty object on failure). */
  payload: Record<string, unknown>;
  /** Present when `ok` is false. */
  message?: string;
}

/**
 * Fetch the live target list for a verb from
 * ``/api/games/{gameId}/actions/{verb}/targets/?org_id={orgId}``.
 *
 * :param gameId: Active game session id.
 * :param verb: The player verb whose targets to fetch.
 * :param orgId: Acting organization id.
 * :returns: The normalized result — never throws.
 */
export async function fetchVerbTargets(
  gameId: string,
  verb: PlayerVerb,
  orgId: string,
): Promise<VerbTargetsResult> {
  const res = await apiGet<Record<string, unknown>>(
    `/api/games/${gameId}/actions/${verb}/targets/?org_id=${orgId}`,
  );

  if (res.status === "error") {
    return { ok: false, payload: {}, message: res.message ?? "Failed to fetch action targets" };
  }

  const payload = (res.data ?? res) as Record<string, unknown>;
  return { ok: true, payload };
}
