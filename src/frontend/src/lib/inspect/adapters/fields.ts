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
