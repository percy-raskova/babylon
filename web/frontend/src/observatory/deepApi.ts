/**
 * Typed client for the Observatory deep-pane endpoints (spec-099).
 *
 * All accept a `source` (live|archive), threaded as a query param. Each
 * function unwraps the standard envelope and returns `null`/`[]` on error so
 * the panes render an empty/unavailable state rather than throw.
 */

import { get } from "@/api/client";

const BASE = "/api/observatory";

export type Source = "live" | "archive";

export interface ChainAnomaly {
  kind: "gap" | "duplicate" | "bad_checkpoint" | "bad_hash";
  tick: number;
  detail: string;
}

export interface VerifyResult {
  session_id: string;
  source: Source;
  valid: boolean;
  min_tick: number | null;
  max_tick: number | null;
  tick_count: number;
  checkpoint_ticks: number[];
  expected_checkpoint_cadence: number;
  /**
   * Names exactly what `valid`/`anomalies` cover: always `"structural"`
   * (tick contiguity + checkpoint cadence + hash FORMAT/length). This is
   * NOT content/tamper verification — `tick_commit.determinism_hash` is a
   * shallow identity hash whose content is never recomputed here (spec-099
   * fix #1/#2/#7; see `observatory.deep_queries` module docstring).
   */
  verification_scope: "structural";
  anomalies: ChainAnomaly[];
}

export interface FlowTypeSummary {
  flow_type: string;
  row_count: number;
  total_magnitude: number;
}

export interface BoundaryFlowRow {
  tick: number;
  source_node_id: string;
  source_kind: string;
  dest_node_id: string;
  dest_kind: string;
  flow_type: string;
  magnitude: number;
}

export interface BoundaryResult {
  session_id: string;
  source: Source;
  from_tick: number;
  to_tick: number;
  by_flow_type: FlowTypeSummary[];
  rows: BoundaryFlowRow[];
  /** True when the raw-row cap was hit — `rows` is not the full result. */
  truncated: boolean;
}

export interface ConservationRow {
  tick: number;
  scale: string;
  invariant_name: string;
  computed_value: number;
  expected_value: number;
  residual: number;
  severity: "ok" | "warn" | "alarm";
}

export interface ConservationResult {
  rows: ConservationRow[];
  /** True when the raw-row cap was hit — `rows` is not the full result. */
  truncated: boolean;
}

export interface DiffResult {
  a: string;
  b: string;
  source: Source;
  national: { tick: number; a_v_sum: number | null; b_v_sum: number | null; delta: number }[];
  commits: {
    a: { min_tick: number | null; max_tick: number | null; tick_count: number };
    b: { min_tick: number | null; max_tick: number | null; tick_count: number };
    tick_count_delta: number;
    range_delta: number;
  };
}

function withSource(params: URLSearchParams, source: Source): string {
  if (source !== "live") {
    params.set("source", source);
  }
  const q = params.toString();
  return q ? `?${q}` : "";
}

export async function fetchVerify(sessionId: string, source: Source): Promise<VerifyResult | null> {
  const res = await get<VerifyResult>(
    `${BASE}/sessions/${sessionId}/verify/${withSource(new URLSearchParams(), source)}`,
  );
  return res.status === "ok" ? res.data : null;
}

export async function fetchBoundary(
  sessionId: string,
  source: Source,
): Promise<BoundaryResult | null> {
  const res = await get<BoundaryResult>(
    `${BASE}/sessions/${sessionId}/boundary/${withSource(new URLSearchParams(), source)}`,
  );
  return res.status === "ok" ? res.data : null;
}

export async function fetchConservation(
  sessionId: string,
  source: Source,
  nonOkOnly = false,
): Promise<ConservationResult> {
  const params = new URLSearchParams();
  if (nonOkOnly) {
    params.set("severity", "non_ok");
  }
  const res = await get<ConservationResult>(
    `${BASE}/sessions/${sessionId}/conservation/${withSource(params, source)}`,
  );
  return res.status === "ok" ? res.data : { rows: [], truncated: false };
}

export async function fetchDiff(a: string, b: string, source: Source): Promise<DiffResult | null> {
  const params = new URLSearchParams({ a, b });
  const res = await get<DiffResult>(`${BASE}/diff/${withSource(params, source)}`);
  return res.status === "ok" ? res.data : null;
}
