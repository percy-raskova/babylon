/**
 * Defensive field extraction for the Inspector tab's `panels.inspector`
 * data — the backend's `inspect_*` endpoints currently stub through the
 * matching snapshot entry (see the legacy `useInspector.ts` docstring),
 * so the wire shape is an untyped `Record<string, unknown>` rather than a
 * generated contract. These readers only ever return a real value when
 * the field is present with the expected type — everything else is
 * `null`, rendered as an honest "no data" by the caller rather than a
 * fabricated default (Constitution III.11).
 */

import type { ConsciousnessVector } from "@/types/game";

export function readNumberField(data: Record<string, unknown> | null, key: string): number | null {
  const v = data?.[key];
  return typeof v === "number" ? v : null;
}

export function readStringField(data: Record<string, unknown> | null, key: string): string | null {
  const v = data?.[key];
  return typeof v === "string" ? v : null;
}

export function readConsciousness(
  data: Record<string, unknown> | null,
): ConsciousnessVector | null {
  const v = data?.consciousness;
  if (v === null || typeof v !== "object") return null;
  const obj = v as Record<string, unknown>;
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
