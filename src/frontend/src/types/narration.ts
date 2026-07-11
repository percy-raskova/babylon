/**
 * Program 16 (Living Map) Lane N — AI-narration types.
 *
 * There is no dedicated narration endpoint in the backend yet
 * (`web/game/narrative_service.py` is a flag-gated LLM narrator
 * scheduled from `resolve_tick`, but its prose only ever rides inside
 * existing wire-payload event bodies). This module DEFINES the frontend
 * contract for a future `GET /api/games/:id/narration/` endpoint — see
 * `src/lib/narration/client.ts` for the documented request/response shape
 * the backend should build to.
 *
 * Constitution III.11 (Loud Failure) governs `NarrationState`: an absent
 * or not-yet-generated narration is never rendered as empty/blank —
 * `"offline"` and `"pending"` are distinct, labeled states.
 */

/** What produced (or didn't produce) a beat, and where it anchors. */
export type NarrationScope = "event" | "tick" | "county" | "endgame";

/** Voice register — mirrors Design Bible §7's two registers. */
export type NarrationRegister = "wire" | "analysis";

/**
 * One narrated beat.
 *
 * `subjectRef` is deliberately untyped beyond `string | null` — its shape
 * depends on `scope` (an event id for `"event"`, a county FIPS for
 * `"county"`, `null` for `"tick"`/`"endgame"` beats that aren't anchored to
 * a single entity). Callers that need a typed ref should resolve through
 * `scope` first.
 */
export interface NarrationBeat {
  /** Deterministic id — stable across refetches of the same tick range. */
  id: string;
  /** The simulation tick this beat narrates. */
  tick: number;
  scope: NarrationScope;
  /** Event id / county FIPS / etc., or `null` when the beat has no single subject. */
  subjectRef: string | null;
  headline: string;
  body: string;
  register: NarrationRegister;
}

/**
 * The narrator's overall availability, independent of whether any beats
 * exist yet:
 *
 * - `"offline"` — `BABYLON_LLM_NARRATOR` is off (or the endpoint doesn't
 *   exist yet). NEVER rendered as silent/empty — always labeled.
 * - `"pending"` — the narrator is on but hasn't produced a beat for the
 *   requested range yet (generation scheduled, not yet materialized).
 * - `"ready"` — at least the narrator itself is live; `beats` may still be
 *   `[]` if nothing has been narrated in the requested range.
 */
export type NarrationState = "offline" | "pending" | "ready";
