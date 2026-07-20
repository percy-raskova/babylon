/**
 * Shared field-dump projection backing the `node`/`edge`/`community`
 * resolver adapters — none of the three have a documented field shape
 * (architecture.md §2.4 only names their endpoints), so this ports the
 * legacy `InspectorPanel.tsx`'s `GenericFields` behavior: render whatever
 * keys the payload carries, honestly reporting an empty payload rather
 * than fabricating placeholder rows (Constitution III.11).
 *
 * Track 1 Task 7 (2026-07-18): this generic dump is the ONE path that can
 * surface a political field completely unfiltered (see
 * `EngineBridge.get_inspector_node`'s docstring) — `vision_masked` names
 * which keys `apply_fog` withheld. Two additive rules on top of the plain
 * dump: (1) `vision_masked`/`vision_approx` themselves are bridge metadata,
 * not domain data — they drive rule 2 below and are never rendered as their
 * own raw-dump rows; (2) a row whose key IS in `vision_masked` gets a `fog`
 * ref (`fogRefFor`) so its "no data" render is a clickable explanation
 * rather than a dead end, never for a field that merely happens to be
 * `null` for an unrelated (non-fog) reason.
 */

import type { BblFormat, InspectionNode, InspectionRef, InspectionRow } from "@/types/inspection";
import { fogRefFor } from "../fogFields";
import { readStringField, readVisionMasked, type RawEntity } from "./fields";

/** Bridge metadata keys `apply_fog` adds — presentational input for rule (2)
 *  above, never rendered as their own raw-dump rows (rule 1). */
const FOG_METADATA_KEYS = new Set(["vision_masked", "vision_approx"]);

function rowForEntry(key: string, value: unknown): InspectionRow {
  if (typeof value === "number") {
    return { label: key, value, format: "decimal2" };
  }
  if (typeof value === "string") {
    return { label: key, value, format: "raw" as BblFormat };
  }
  if (value === null) {
    return { label: key, value: null, format: "raw" };
  }
  return { label: key, value: JSON.stringify(value), format: "raw" };
}

export function adaptGenericEntity(ref: InspectionRef, data: RawEntity): InspectionNode {
  const maskedFields = readVisionMasked(data);
  const nodeType = readStringField(data, "type") ?? "unknown";
  const fallbackName = readStringField(data, "name") ?? readStringField(data, "id");

  const entries = Object.entries(data).filter(([key]) => !FOG_METADATA_KEYS.has(key));
  const rows: InspectionRow[] =
    entries.length === 0
      ? [{ label: "Detail", value: null, format: "raw" }]
      : entries.map(([key, value]) => ({
          ...rowForEntry(key, value),
          ref: fogRefFor(key, maskedFields, nodeType, ref.id, fallbackName),
        }));

  return {
    ref,
    title: ref.label ?? fallbackName ?? ref.id,
    sections: [{ rows }],
  };
}
