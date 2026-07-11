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
  | "hex"
  | "org"
  | "node"
  | "edge"
  | "community"
  | "metric"
  | "formula";

/**
 * A pointer to something inspectable. `scope` disambiguates instance data
 * from global aggregates, e.g. `"hex:<h3>"`, `"org:<id>"`, `"global"`.
 */
export interface InspectionRef {
  kind: InspectionRefKind;
  id: string;
  scope?: string;
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
