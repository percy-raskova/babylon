/**
 * Observatory payload types — mirror the `/api/observatory/*` contract
 * (spec-096, see specs/096-observatory-foundation/contracts/observatory-api.md).
 */

/** One session with committed ticks in the simulation DB. */
export interface ObservatorySession {
  session_id: string;
  min_tick: number;
  max_tick: number;
  tick_count: number;
  checkpoint_count: number;
  latest_hash: string | null;
  scenario: string | null;
  status: string | null;
  created_at: string | null;
}

/** Committed tick range + checkpoint ticks for one session. */
export interface TickRange {
  session_id: string;
  min_tick: number;
  max_tick: number;
  tick_count: number;
  checkpoint_ticks: number[];
}

export type Scope = "national" | "state" | "county";

/** One value-aggregate point at a committed tick. */
export interface ValueAggregatePoint {
  tick: number;
  c_sum: number;
  v_sum: number;
  s_sum: number;
  k_sum: number;
  biocapacity_sum: number;
  hex_count: number;
}

/** A value-aggregate series over a tick range. */
export interface Series {
  session_id: string;
  scope: Scope;
  scope_id: string;
  from_tick: number;
  to_tick: number;
  points: ValueAggregatePoint[];
}

/** One entry in the tick-commit hash chain. */
export interface CommitRecord {
  tick: number;
  determinism_hash: string;
  hex_rows_written: number;
  is_checkpoint: boolean;
  created_at_utc: string | null;
}

/** Feature-flag probe result. */
export interface ObservatoryStatus {
  enabled: boolean;
  sim_alias: string;
}

/** The metric columns a series exposes (also the CSV column order). */
export type SeriesMetric = "c_sum" | "v_sum" | "s_sum" | "k_sum" | "biocapacity_sum" | "hex_count";

export const SERIES_METRICS: SeriesMetric[] = [
  "c_sum",
  "v_sum",
  "s_sum",
  "k_sum",
  "biocapacity_sum",
  "hex_count",
];
