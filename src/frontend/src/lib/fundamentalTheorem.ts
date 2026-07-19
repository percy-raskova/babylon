/**
 * Pure derivations for the Fundamental Theorem meter (Track 2 / T2-6,
 * spec-117). Everything here is deterministic arithmetic over the
 * `/economy/` dashboard payload — no fetches, no randomness. Reuses the
 * backend's own `core_wages - wealth` sign convention (positive = an
 * imperial subsidy) rather than recomputing it: `imperial_rent_gap` /
 * `imperial_rent_gap_by_region` are both already the correctly-signed,
 * correctly-weighted result (see `EngineBridge.get_economy_dashboard` /
 * `_imperial_rent_gap_by_region`'s docstrings) — this module only shapes
 * that data for display, it never re-derives the gap itself.
 */

import type { EconomyDashboardPayload, ImperialRentGapRegion } from "@/types/game";

/** The graph-wide Wc/Vc/gap reading. */
export interface FundamentalTheoremReading {
  /** Core wages paid, graph-wide (W_c). */
  wc: number;
  /** Value produced, graph-wide (V_c). */
  vc: number;
  /** W_c - V_c — positive is an imperial subsidy. */
  gap: number;
  hasSubsidy: boolean;
}

/**
 * The graph-wide Fundamental Theorem reading, or `null` when the graph has
 * no economic activity recorded yet (`has_data: false` — Constitution
 * III.11, never a fabricated zero reading).
 */
export function deriveFundamentalTheoremReading(
  payload: EconomyDashboardPayload,
): FundamentalTheoremReading | null {
  if (!payload.has_data) return null;
  return {
    wc: payload.wage_flow_total,
    vc: payload.value_produced,
    gap: payload.imperial_rent_gap,
    hasSubsidy: payload.imperial_rent_gap > 0,
  };
}

/**
 * The apologist-refutation narrative at graph scale — echoes the per-class
 * inspector copy (`_social_class_inspector_fields`'s `apologist_refutation`)
 * but for the whole graph's aggregate reading.
 */
export function fundamentalTheoremNarrative(reading: FundamentalTheoremReading): string {
  if (reading.hasSubsidy) {
    return (
      `Core wages (${reading.wc.toFixed(1)}) exceed value produced (${reading.vc.toFixed(1)}) ` +
      `by ${reading.gap.toFixed(1)} — an imperial subsidy transferred from the periphery, the ` +
      "material basis of labor-aristocracy loyalty, not a return to skill."
    );
  }
  return (
    "No aggregate imperial subsidy: core wages do not exceed value produced " +
    `(gap=${reading.gap.toFixed(1)}).`
  );
}

/**
 * The per-region breakdown rows, sorted worst-subsidy-first (largest
 * positive `gap_per_capita` first) so the Circuit screen's table reads
 * "who benefits most" at a glance. The backend already sorts by
 * `territory_id` for determinism; this is a purely presentational re-sort,
 * stable for ties (`Array.prototype.sort` is a stable sort per spec).
 */
export function sortRegionsByGapDescending(
  rows: readonly ImperialRentGapRegion[],
): ImperialRentGapRegion[] {
  return [...rows].sort((a, b) => b.gap_per_capita - a.gap_per_capita);
}
