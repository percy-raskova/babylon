/**
 * `hex`-kind resolver adapter — `GET /api/games/:id/hex/:h3/`
 * (architecture.md §2.4, `EngineBridge.get_inspector_hex`). Ported field
 * set from the legacy `InspectorPanel.tsx`'s `TerritoryFields`, extended
 * with `county_name`/`dominant_class` (present on `StubEngineBridge`'s
 * canned payload) and an "explain" ref on `profit_rate` (the one
 * hex-scoped metric in the provenance mirror).
 */

import type { InspectionNode, InspectionRef, InspectionRow } from "@/types/inspection";
import type { TerritoryState } from "@/types/game";
import { explainRefFor } from "../provenance";
import { readNumberField, readStringField, type RawEntity } from "./fields";

/**
 * Project a clicked `TerritoryState` (the per-hex feature a map click carries)
 * into the `RawEntity` key shape :func:`adaptHex` reads, so a hex click renders
 * a real card from data already in hand — the same authoritative values the
 * hover `HexTooltip` shows — with no `get_inspector_hex` round-trip.
 *
 * Only the fields a `TerritoryState` genuinely carries are mapped;
 * `dominant_class` and `profit_rate` (engine-side enrichments the click cannot
 * see) are deliberately OMITTED, so `adaptHex` renders them as honest nulls
 * rather than fabricated defaults (Constitution III.11). `name` becomes
 * `county_name` (the card's title/first row); a `null` habitability stays null.
 */
export function territoryToHexInline(territory: TerritoryState): RawEntity {
  const raw: RawEntity = {
    county_name: territory.name,
    population: territory.population,
    biocapacity: territory.biocapacity,
    heat: territory.heat,
    rent_level: territory.rent_level,
  };
  if (territory.habitability != null) {
    raw.habitability = territory.habitability;
  }
  return raw;
}

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
