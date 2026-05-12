/**
 * Spec 061 T054 / FR-026: timeseries payload type.
 *
 * Mirrors the response shape of GET /api/games/<id>/timeseries/.
 * Each metric array is parallel-indexed with `ticks` (oldest first);
 * `null` entries indicate the source tick_summary row was missing that
 * column and the frontend should skip / interpolate.
 */

export interface TimeseriesPayload {
  /** Ascending tick numbers — the x-axis for the six metric arrays. */
  ticks: number[];
  /** Phi (imperial rent) per tick. */
  imperial_rent: (number | null)[];
  /** Average consciousness per tick. */
  consciousness: (number | null)[];
  /** Aggregate solidarity (edge count proxy) per tick. */
  solidarity: (number | null)[];
  /** Heat total per tick (carceral pressure). */
  heat: (number | null)[];
  /** Total wealth across all entities per tick. */
  wealth: (number | null)[];
  /** Biocapacity per tick (metabolic rift indicator). */
  biocapacity: (number | null)[];
}
