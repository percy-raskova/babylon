/**
 * The frozen InspectionStack data model (architecture.md §2.2). Lane A owns
 * this contract as *types only* — the resolvers, adapters, store slice
 * (`store/slices/inspectSlice.ts`), and rendering components
 * (`components/inspect/*`) belong to Lane C; the additive `/explain/`
 * backend belongs to Lane D. Both consume these shapes without
 * modification.
 *
 * Recursion is uniform: an `InspectionNode` renders as a card of
 * `InspectionSection`s of `InspectionRow`s; any row carrying a `ref`
 * pushes a new `InspectionNode` frame when clicked (entity → metric →
 * formula → input-metric → …), bottoming out at constants/state values.
 */

/** What an `InspectionRef` points at — one resolver per kind (Lane C). */
export type InspectionRefKind =
  "hex" | "org" | "node" | "edge" | "community" | "metric" | "formula";

/**
 * A pointer to something inspectable. `scope` disambiguates instance data
 * from global aggregates, e.g. `"hex:<h3>"`, `"org:<id>"`, `"global"`.
 *
 * `label` (Lane C, additive — DESIGN_BIBLE.md §4 "same-name discipline"):
 * when a ref is pushed from a click on an `InspectionRow`, the pusher sets
 * `label` to that row's exact `label` text, so the resolved child frame's
 * title can equal the parent row's label verbatim rather than the
 * resolver re-deriving a (possibly differently-worded) title from the
 * fetched payload. Root frames pushed from outside a row (StatChip, map
 * selection) omit it — their title falls back to the resolved entity's
 * own name field.
 */
export interface InspectionRef {
  kind: InspectionRefKind;
  id: string;
  scope?: string;
  label?: string;
}

/**
 * How `InspectionRow.value` should be rendered by the `BblData` formatting
 * layer (Lane C's `ValueRow`). Constitution III.11 null-honesty: a `null`
 * value renders "no data" regardless of `format`, never a fabricated 0.
 */
export type BblFormat = "integer" | "decimal2" | "decimal3" | "percent" | "raw";

/** One slice of a composition/breakdown row (consciousness vector, wealth_by_class_role, …). */
export interface InspectionCompositionEntry {
  key: string;
  value: number;
  color?: string;
}

/** One labeled value in an `InspectionSection`. */
export interface InspectionRow {
  label: string;
  value: number | string | null;
  format: BblFormat;
  /** Present when this row is itself explainable — clicking pushes a child frame. */
  ref?: InspectionRef;
  /** Present for composition/breakdown rows rendered as a `BreakdownBar`. */
  composition?: InspectionCompositionEntry[];
  /**
   * Comparison baseline (DESIGN_BIBLE.md §4 "every stat row shows its
   * comparison baseline") — a per-tick series ending at the row's current
   * value, rendered as a `Sparkline` with realized min/max labeled inline.
   * Omitted (not `[]`) when the backing endpoint carries no history for
   * this row — absence, not an empty series, is the honest signal.
   */
  history?: number[];
}

/** A grouped block of rows within an `InspectionNode`; `label` is optional (ungrouped). */
export interface InspectionSection {
  label?: string;
  rows: InspectionRow[];
}

/** One fully-resolved InspectionStack frame's content. */
export interface InspectionNode {
  ref: InspectionRef;
  title: string;
  sections: InspectionSection[];
}

/**
 * `GET /api/games/:id/explain/?metric=<name>&scope=<scope>` response body
 * (architecture.md §2.4, `web/game/api.py::_explain_result_to_dict`).
 * Additive — Lane D's live contract, mirrored here so
 * `lib/inspect/adapters/metric.ts` and `api/client.ts::fetchExplain` share
 * one typed shape instead of `Record<string, unknown>`.
 */
export interface ExplainInput {
  name: string;
  label: string;
  value: number | string | null;
  kind: "metric" | "constant" | "state";
  ref: string | null;
}

export interface ExplainFormula {
  name: string | null;
  expression: string;
  doc: string;
}

export interface ExplainResponse {
  metric: string;
  scope: string;
  value: number | null;
  formula: ExplainFormula;
  inputs: ExplainInput[];
  constants: ExplainInput[];
}
