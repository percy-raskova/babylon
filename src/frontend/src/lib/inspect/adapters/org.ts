/**
 * `org`-kind resolver adapter — `GET /api/games/:id/org/:id/`
 * (architecture.md §2.4, `EngineBridge.get_inspector_org`). Ported field
 * set from the legacy `InspectorPanel.tsx`'s `OrgFields`/
 * `ConsciousnessBreakdown` (now a `composition` row rendered by
 * `BreakdownBar`), extended with "explain" refs for the four org-scoped
 * provenance-mirror metrics when the raw payload carries a matching field.
 */

import type { InspectionNode, InspectionRef, InspectionRow } from "@/types/inspection";
import { explainRefFor } from "../provenance";
import { readConsciousness, readNumberField, readStringField, type RawEntity } from "./fields";

const CONSCIOUSNESS_COLORS = {
  revolutionary: "text-laser",
  liberal: "text-cadre",
  fascist: "text-rupture",
} as const;

export function adaptOrg(ref: InspectionRef, data: RawEntity): InspectionNode {
  const scope = `org:${ref.id}`;
  const name = readStringField(data, "name");
  const consciousness = readConsciousness(data);

  const rows: InspectionRow[] = [
    {
      label: "Class Character",
      value: readStringField(data, "class_character") ?? readStringField(data, "type"),
      format: "raw",
    },
    {
      label: "Budget",
      value: readNumberField(data, "budget") ?? readNumberField(data, "funds"),
      format: "decimal2",
    },
    { label: "Cohesion", value: readNumberField(data, "cohesion"), format: "decimal2" },
    { label: "Heat", value: readNumberField(data, "heat"), format: "decimal2" },
    {
      label: "Consciousness",
      value: null,
      format: "raw",
      composition: consciousness
        ? [
            {
              key: "Revolutionary",
              value: consciousness.revolutionary,
              color: CONSCIOUSNESS_COLORS.revolutionary,
            },
            { key: "Liberal", value: consciousness.liberal, color: CONSCIOUSNESS_COLORS.liberal },
            {
              key: "Fascist",
              value: consciousness.fascist,
              color: CONSCIOUSNESS_COLORS.fascist,
            },
          ]
        : undefined,
    },
    {
      label: "Labor Aristocracy Ratio",
      value: readNumberField(data, "labor_aristocracy_ratio"),
      format: "decimal3",
      ref: explainRefFor("labor_aristocracy_ratio", scope, "org", "Labor Aristocracy Ratio"),
    },
    {
      label: "Revolution Probability",
      value: readNumberField(data, "revolution_probability"),
      format: "decimal3",
      ref: explainRefFor("revolution_probability", scope, "org", "Revolution Probability"),
    },
    {
      label: "Acquiescence Probability",
      value: readNumberField(data, "acquiescence_probability"),
      format: "decimal3",
      ref: explainRefFor("acquiescence_probability", scope, "org", "Acquiescence Probability"),
    },
    {
      label: "Consciousness Drift",
      value: readNumberField(data, "consciousness_drift"),
      format: "decimal3",
      ref: explainRefFor("consciousness_drift", scope, "org", "Consciousness Drift"),
    },
  ];

  return {
    ref,
    title: ref.label ?? name ?? ref.id,
    sections: [{ rows }],
  };
}
