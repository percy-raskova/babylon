/**
 * fetchNarration — store-free client for the narration contract endpoint.
 *
 * ``GET /api/games/{gameId}/narration/?since_tick={sinceTick}``
 *
 * Program 16 Lane N defined this contract before the backend existed;
 * Program 20 Track B (task B5) implemented the real view
 * (`web/game/api.py::game_narration`, reading `NarrationRecord` — task B4).
 * Routes through the typed endpoint registry (`@/api/endpoints`'s
 * `narration` entry) rather than a literal URL. A 404 can still occur for
 * other reasons (unknown/foreign game id) and degrades the same as any
 * other error — see below.
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
 * :Response (404) / (other errors / network failure): also degrades to
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
import { endpoints } from "@/api/endpoints";
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
  const res = await apiGet<NarrationFetchResult>(
    `${endpoints.narration.path({ id: gameId })}${query}`,
  );

  if (res.status === "error") {
    return OFFLINE;
  }

  return res.data;
}
