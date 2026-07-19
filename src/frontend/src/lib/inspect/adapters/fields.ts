/**
 * Defensive field extraction for the InspectionStack's entity resolvers
 * (`hex`/`org`/`node`/`edge`/`community`) — ported from the legacy
 * `lib/inspectorFields.ts` (spec-113 Lane C absorbs `components/inspector/*`).
 * The backend's `inspect_*` endpoints stub through the matching snapshot
 * entry (see `EngineBridge.get_inspector_hex` et al.'s docstrings) with an
 * untyped `Record<string, unknown>` wire shape, so these readers only ever
 * return a real value when the field is present with the expected type —
 * everything else is `null`, rendered as an honest "no data" by
 * `ValueRow` rather than a fabricated default (Constitution III.11).
 */

import type { ConsciousnessVector } from "@/types/game";

export type RawEntity = Record<string, unknown>;

export function readNumberField(data: RawEntity | null, key: string): number | null {
  const v = data?.[key];
  return typeof v === "number" ? v : null;
}

export function readStringField(data: RawEntity | null, key: string): string | null {
  const v = data?.[key];
  return typeof v === "string" ? v : null;
}

/** The field names Track 1's `apply_fog` masked to `null` on this payload
 *  (`web/game/fog/filter.py`'s `vision_masked`), or `[]` when absent/
 *  malformed — never throws, mirrors every other reader here's "honest
 *  absence over fabrication" contract (Constitution III.11). */
export function readVisionMasked(data: RawEntity | null): string[] {
  const v = data?.vision_masked;
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

export function readConsciousness(data: RawEntity | null): ConsciousnessVector | null {
  const v = data?.consciousness;
  if (v === null || typeof v !== "object") return null;
  const obj = v as RawEntity;
  const { liberal, fascist, revolutionary } = obj;
  if (
    typeof liberal === "number" &&
    typeof fascist === "number" &&
    typeof revolutionary === "number"
  ) {
    return { liberal, fascist, revolutionary };
  }
  return null;
}
