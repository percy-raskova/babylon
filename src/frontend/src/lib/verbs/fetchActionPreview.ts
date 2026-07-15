/**
 * fetchActionPreview — live action-preview fetch, store-free.
 *
 * Mirrors `fetchVerbTargets`'s pure fetch-and-normalize shape (Program 17
 * Wave 1 item W1.2 — replaces the fake constant-direction predictedEffect
 * chips with this real backend call). Unlike the per-verb target endpoints,
 * `POST /actions/preview/` returns the standard `{status, data, ...}`
 * envelope (`api/client`'s `post()` already parses it), so there is no
 * flat-body quirk to unwrap here.
 */

import { post as apiPost } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import type { ActionPreviewResult } from "@/types/game";

export interface ActionPreviewFetchResult {
  /** False when the request failed (network error or HTTP/API error). */
  ok: boolean;
  /** The preview payload, or null on failure. */
  data: ActionPreviewResult | null;
  /** Present when `ok` is false. */
  message?: string;
}

/**
 * Fetch a live action preview from ``POST /api/games/{gameId}/actions/preview/``.
 *
 * :param gameId: Active game session id.
 * :param orgId: Acting organization id.
 * :param verb: The player verb being previewed — rides in the body here
 *  (unlike submit, where the verb rides in the URL, Spec 040 §6.1).
 * :param targetId: Optional target id; sent as `null` when none is selected.
 * :returns: The normalized result — never throws.
 *
 * NOTE: only org_id/verb/target_id are sent. The backend's preview_action
 * serializer accepts no params payload yet, so mode-sensitive preview (e.g.
 * attack's targeted vs mass mode) is unplumbed backend-side.
 */
export async function fetchActionPreview(
  gameId: string,
  orgId: string,
  verb: string,
  targetId?: string | null,
): Promise<ActionPreviewFetchResult> {
  const res = await apiPost<ActionPreviewResult>(endpoints.actionsPreview.path({ id: gameId }), {
    org_id: orgId,
    verb,
    target_id: targetId ?? null,
  });

  if (res.status === "error") {
    return { ok: false, data: null, message: res.message ?? "Failed to fetch action preview" };
  }

  return { ok: true, data: res.data };
}
