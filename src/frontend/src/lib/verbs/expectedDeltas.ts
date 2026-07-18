/**
 * Shared wire→VerbTarget mapping for the `expected_deltas` row sub-object
 * the educate/aid/attack GET targets endpoints emit (spec-116 FR-116-4.4,
 * ExpectedDeltasSerializer in web/game/serializers.py). A null wire axis
 * means "no per-target formula exists for this verb" — it is dropped,
 * never coerced to 0 (honest absence, Constitution III.11).
 */

import type { VerbTarget } from "./types";

/** The row sub-object as serialized by ExpectedDeltasSerializer. */
export interface WireExpectedDeltas {
  consciousness_delta?: number | null;
  heat_delta?: number | null;
}

export function parseExpectedDeltas(
  raw: WireExpectedDeltas | undefined,
): VerbTarget["expectedDeltas"] {
  if (!raw) return undefined;
  const out: NonNullable<VerbTarget["expectedDeltas"]> = {};
  if (typeof raw.consciousness_delta === "number" && Number.isFinite(raw.consciousness_delta)) {
    out.consciousness = raw.consciousness_delta;
  }
  if (typeof raw.heat_delta === "number" && Number.isFinite(raw.heat_delta)) {
    out.heat = raw.heat_delta;
  }
  return Object.keys(out).length > 0 ? out : undefined;
}
