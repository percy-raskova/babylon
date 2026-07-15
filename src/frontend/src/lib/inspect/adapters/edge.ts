/**
 * `edge`-kind resolver adapter — `GET /api/games/:id/edge/:id/`.
 *
 * Audit Wave 4 straggler (task #76): `history` (an optional third
 * argument, `resolveRef`'s edge-only second fetch to
 * `GET /api/games/:id/edge/:id/history/`) is spliced onto the generic
 * field-dump's `value_flow` row (every edge type carries this — the one
 * universal numeric "weight") and, when present, the `solidarity_strength`
 * row (only `edge_type === "solidarity"` edges carry this field at all —
 * the audit brief's "distinct visual treatment for CLIENT_STATE/SOLIDARITY
 * edges"). `ValueRow` already renders any row carrying `.history` as a
 * `Sparkline` (DESIGN_BIBLE.md §4 "every stat row shows its comparison
 * baseline") — this is the first adapter to actually populate that
 * previously-dead field.
 */

import type { InspectionNode, InspectionRef, InspectionRow } from "@/types/inspection";
import type { EdgeHistoryPoint } from "@/types/game";
import { adaptGenericEntity } from "./genericEntity";
import type { RawEntity } from "./fields";

/** Finite, non-null readings only — a gap in the recorded series is
 * silently skipped rather than plotted at a guessed value (matches
 * `DuelSparkline`'s own null-handling convention). */
function finiteSeries(history: EdgeHistoryPoint[], key: "weight" | "solidarity"): number[] {
  return history
    .map((point) => point[key])
    .filter((value): value is number => value !== null && Number.isFinite(value));
}

/** Attach `.history` to `row` when `series` has at least one real reading. */
function withHistory(row: InspectionRow, series: number[]): InspectionRow {
  return series.length > 0 ? { ...row, history: series } : row;
}

export function adaptEdge(
  ref: InspectionRef,
  data: RawEntity,
  history: EdgeHistoryPoint[] = [],
): InspectionNode {
  const node = adaptGenericEntity(ref, data);
  if (history.length === 0) return node;

  const weights = finiteSeries(history, "weight");
  const solidarity = finiteSeries(history, "solidarity");
  const section = node.sections[0];
  if (!section) return node;

  const rows = section.rows.map((row) => {
    if (row.label === "value_flow") return withHistory(row, weights);
    if (row.label === "solidarity_strength") return withHistory(row, solidarity);
    return row;
  });

  return { ...node, sections: [{ ...section, rows }] };
}
