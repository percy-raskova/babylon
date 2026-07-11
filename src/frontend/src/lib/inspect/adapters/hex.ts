/**
 * `hex`-kind resolver adapter — `GET /api/games/:id/hex/:h3/`
 * (architecture.md §2.4, `EngineBridge.get_inspector_hex`). Ported field
 * set from the legacy `InspectorPanel.tsx`'s `TerritoryFields`, extended
 * with `county_name`/`dominant_class` (present on `StubEngineBridge`'s
 * canned payload) and an "explain" ref on `profit_rate` (the one
 * hex-scoped metric in the provenance mirror).
 */

import type { InspectionNode, InspectionRef, InspectionRow } from "@/types/inspection";
import { explainRefFor } from "../provenance";
import { readNumberField, readStringField, type RawEntity } from "./fields";

export function adaptHex(ref: InspectionRef, data: RawEntity): InspectionNode {
  const scope = `hex:${ref.id}`;
  const countyName = readStringField(data, "county_name");

  const rows: InspectionRow[] = [
    { label: "County", value: countyName, format: "raw" },
    { label: "Population", value: readNumberField(data, "population"), format: "integer" },
    { label: "Habitability", value: readNumberField(data, "habitability"), format: "decimal2" },
    { label: "Biocapacity", value: readNumberField(data, "biocapacity"), format: "decimal2" },
    { label: "Heat", value: readNumberField(data, "heat"), format: "decimal2" },
    { label: "Rent Level", value: readNumberField(data, "rent_level"), format: "decimal2" },
    { label: "Dominant Class", value: readStringField(data, "dominant_class"), format: "raw" },
    {
      label: "Profit Rate",
      value: readNumberField(data, "profit_rate"),
      format: "decimal3",
      ref: explainRefFor("profit_rate", scope, "hex", "Profit Rate"),
    },
  ];

  return {
    ref,
    title: ref.label ?? countyName ?? ref.id,
    sections: [{ rows }],
  };
}
