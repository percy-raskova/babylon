/**
 * groups.ts — the Paradox-style lens grouping for `MapLensBar` (spec-113 §3.1,
 * DESIGN_BIBLE.md §3.1's taxonomy).
 *
 * The Design Bible's roster table (§3.2) uses a 5th "Social" group for one
 * starred lens (class composition) alongside the four the architecture/task
 * brief names explicitly (Extraction/Struggle/Political/Reproduction) — this
 * registry folds `class_composition` into **Political** (bible §3.2's own
 * "National oppression" Political-group entry is the closest thematic
 * cousin: both read class/national stratification off the map). Documented
 * here rather than silently decided in `registry.ts` so the choice is easy
 * to revisit.
 */

export type LensGroupId = "extraction" | "struggle" | "political" | "reproduction";

export interface LensGroupDef {
  id: LensGroupId;
  /** Display label for the group header in `MapLensBar`. */
  label: string;
}

/** Bar order — matches DESIGN_BIBLE.md §3.2's table row order. */
export const LENS_GROUPS: readonly LensGroupDef[] = [
  { id: "extraction", label: "Extraction" },
  { id: "struggle", label: "Struggle" },
  { id: "political", label: "Political" },
  { id: "reproduction", label: "Reproduction" },
];
