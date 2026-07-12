/**
 * Shared field-dump projection backing the `node`/`edge`/`community`
 * resolver adapters — none of the three have a documented field shape
 * (architecture.md §2.4 only names their endpoints), so this ports the
 * legacy `InspectorPanel.tsx`'s `GenericFields` behavior: render whatever
 * keys the payload carries, honestly reporting an empty payload rather
 * than fabricating placeholder rows (Constitution III.11).
 */

import type { BblFormat, InspectionNode, InspectionRef, InspectionRow } from "@/types/inspection";
import { readStringField, type RawEntity } from "./fields";

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
  const entries = Object.entries(data);
  const rows: InspectionRow[] =
    entries.length === 0
      ? [{ label: "Detail", value: null, format: "raw" }]
      : entries.map(([key, value]) => rowForEntry(key, value));

  const fallbackName = readStringField(data, "name") ?? readStringField(data, "id");

  return {
    ref,
    title: ref.label ?? fallbackName ?? ref.id,
    sections: [{ rows }],
  };
}
