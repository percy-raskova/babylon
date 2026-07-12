/**
 * `metric`/`formula`-kind resolver adapter — projects the `/explain/`
 * response (architecture.md §2.4) onto the terminal FormulaCard frame:
 * value, expression, per-input rows (each recursively explainable when
 * the backend marks it `kind: "metric"`), and a constants section with
 * provenance notes (DESIGN_BIBLE.md §4's "terminal frames are
 * FormulaCards").
 *
 * "Wages never naked" (DESIGN_BIBLE.md §4, binding): `core_wages` never
 * appears without `value_produced` in the same section. This adapter does
 * NOT reorder or filter `data.inputs` — it renders them in the exact
 * order `web/game/provenance.py` emits them, where `core_wages` and
 * `value_produced` are always adjacent entries in the same input list
 * (verified against the manifest source for `labor_aristocracy_ratio`/
 * `consciousness_drift`, both org-scoped and both wage-bearing) — the
 * pairing is a property of the backend contract this adapter preserves,
 * not one it re-derives.
 */

import type {
  ExplainResponse,
  InspectionNode,
  InspectionRef,
  InspectionRow,
  InspectionSection,
} from "@/types/inspection";

function inputRow(scope: string, input: ExplainResponse["inputs"][number]): InspectionRow {
  const ref: InspectionRef | undefined =
    input.kind === "metric" && input.ref !== null
      ? { kind: "metric", id: input.ref, scope, label: input.label }
      : undefined;
  return {
    label: input.label,
    value: input.value,
    format: typeof input.value === "number" ? "decimal3" : "raw",
    ref,
  };
}

export function adaptMetric(ref: InspectionRef, data: ExplainResponse): InspectionNode {
  const scope = ref.scope ?? data.scope;

  const sections: InspectionSection[] = [
    {
      label: "Formula",
      rows: [
        { label: "Value", value: data.value, format: "decimal3" },
        { label: "Expression", value: data.formula.expression, format: "raw" },
      ],
    },
  ];

  if (data.inputs.length > 0) {
    sections.push({
      label: "Inputs",
      rows: data.inputs.map((input) => inputRow(scope, input)),
    });
  }

  if (data.constants.length > 0) {
    sections.push({
      label: "Constants",
      rows: data.constants.map((c) => ({
        label: c.label,
        value: c.value,
        format: typeof c.value === "number" ? "decimal3" : "raw",
      })),
    });
  }

  sections.push({
    label: "Provenance",
    rows: [{ label: "Source", value: data.formula.doc || null, format: "raw" }],
  });

  return {
    ref,
    title: ref.label ?? data.formula.name ?? data.metric,
    sections,
  };
}
