/**
 * fetchVerbEligibility — per-verb eligibility fetch, store-free (spec-116
 * FR-4.8). Unlike the per-verb target endpoints (flat bodies, see
 * `fetchVerbTargets`), `GET /actions/eligibility/` is a new surface and
 * uses the standard `{status, data}` envelope — same normalization shape
 * as `fetchActionPreview`.
 */

import { get as apiGet } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import type { VerbEligibilityPayload } from "@/types/game";

export interface VerbEligibilityFetchResult {
  /** False when the request failed (network error or HTTP/API error). */
  ok: boolean;
  /** The eligibility payload, or null on failure. */
  data: VerbEligibilityPayload | null;
  /** Present when `ok` is false. */
  message?: string;
}

/**
 * Fetch per-verb eligibility from
 * ``/api/games/{gameId}/actions/eligibility/?org_id={orgId}``.
 *
 * :param gameId: Active game session id.
 * :param orgId: Acting organization id.
 * :returns: The normalized result — never throws.
 */
export async function fetchVerbEligibility(
  gameId: string,
  orgId: string,
): Promise<VerbEligibilityFetchResult> {
  const res = await apiGet<VerbEligibilityPayload>(
    `${endpoints.verbEligibility.path({ id: gameId })}?org_id=${orgId}`,
  );
  if (res.status === "error" || !res.data) {
    return {
      ok: false,
      data: null,
      message: res.message ?? "Failed to fetch verb eligibility",
    };
  }
  return { ok: true, data: res.data };
}
