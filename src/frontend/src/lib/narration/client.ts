/**
 * fetchNarration — store-free client for the narration contract endpoint.
 *
 * ``GET /api/games/{gameId}/narration/?since_tick={sinceTick}``
 *
 * This endpoint DOES NOT EXIST in the backend yet (2026-07-11). Program 16
 * Lane N defines this contract so the frontend has typed slots to mount AI
 * narration into now, and the backend implementer (the eventual
 * `web/game/narrative_service.py` wiring, or a new view) has a spec to
 * build to. Until it exists, every call 404s and this client reports that
 * as the honest `"offline"` state (Constitution III.11 — absent value
 * renders as "no data"/"offline", never a fabricated empty-but-ready UI).
 *
 * :Request: ``since_tick`` (optional, integer) — only return beats at or
 *     after this tick. Omitted on the first fetch; a caller that wants to
 *     poll incrementally should pass the highest `tick` it has already
 *     received.
 * :Response (200): standard `{status: "ok", data: NarrationFetchResult}`
 *     envelope, where::
 *
 *         NarrationFetchResult = {
 *           status: "offline" | "pending" | "ready",  // NarrationState
 *           beats: NarrationBeat[],
 *         }
 *
 *     `status` here is the domain state (see `types/narration.ts`), NOT
 *     the envelope's own `ok`/`error` discriminant — the two are distinct
 *     fields at different nesting levels.
 * :Response (404): the endpoint isn't implemented yet. Treated identically
 *     to a live endpoint reporting `"offline"`.
 * :Response (other errors / network failure): also degrades to
 *     `{status: "offline", beats: []}` — this client never throws and
 *     never fabricates `"ready"` from a failed request. A future caller
 *     that needs to distinguish "narrator off" from "request failed"
 *     should extend `NarrationState` with a 4th value rather than
 *     overload this client's return shape.
 *
 * :param gameId: Active game session id.
 * :param sinceTick: Optional lower bound (inclusive) on `tick`.
 * :returns: `{status, beats}` — never throws.
 */

import { get as apiGet } from "@/api/client";
import type { NarrationBeat, NarrationState } from "@/types/narration";

export interface NarrationFetchResult {
  status: NarrationState;
  beats: NarrationBeat[];
}

const OFFLINE: NarrationFetchResult = { status: "offline", beats: [] };

export async function fetchNarration(
  gameId: string,
  sinceTick?: number,
): Promise<NarrationFetchResult> {
  const query = sinceTick !== undefined ? `?since_tick=${sinceTick}` : "";
  const res = await apiGet<NarrationFetchResult>(`/api/games/${gameId}/narration/${query}`);

  if (res.status === "error") {
    return OFFLINE;
  }

  return res.data;
}
