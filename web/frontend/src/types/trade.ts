/**
 * Spec 103: Trade surfaces — TypeScript types matching the three contracts.
 *
 * Mirrors `specs/103-trade-surfaces/contracts/{trade-flows,county-exposure,
 * trade-panel}.yaml`. All three payloads are served by GET-only endpoints
 * reading persisted engine state (Constitution III: AI observes).
 */

import type { ApiResponse } from "@/types/game";
export type { ApiResponse };

// ---------------------------------------------------------------------------
// Trade Flows — GET /api/games/:id/trade-flows/ (Wire INDEX per-bloc lines)
// ---------------------------------------------------------------------------

export interface FlowPoint {
  tick: number;
  magnitude: number;
}

export interface BlocLatest {
  phi_year_inflow: number;
  bilateral_trade_value: number;
  bilateral_trade_tons: number;
  erdi_ratio: number;
}

export interface BlocFlowEntry {
  node_id: string;
  label: string;
  kind: "international" | "domestic_rest";
  latest: BlocLatest;
  phi_series: FlowPoint[];
  trade_series: FlowPoint[];
}

export interface TradeFlowsPayload {
  tick: number;
  has_data: boolean;
  blocs: BlocFlowEntry[];
}

// ---------------------------------------------------------------------------
// County Exposure — GET /api/games/:id/exposure/?county_fips= (Territory Detail)
// ---------------------------------------------------------------------------

export type SourceKind = "reference_table" | "dynamic_table" | "derived";

export interface SourceRef {
  kind: SourceKind;
  path: string;
}

export interface Contributor {
  label: string;
  value: number;
  share: number;
  source: SourceRef;
  children: Contributor[];
}

export interface Breakdown {
  total: number;
  contributors: Contributor[];
}

export interface Citation {
  id: string;
  source: string;
  table: string;
  year?: number | string;
  notes?: string;
}

export interface ExposurePayload {
  county_fips: string;
  has_data: boolean;
  total_exposure: number;
  breakdown: Breakdown;
  citations: Citation[];
}

// ---------------------------------------------------------------------------
// Trade Panel — GET /api/games/:id/trade-panel/ (Analysis page)
// ---------------------------------------------------------------------------

export type FlowType = "drain_edge" | "trade_inbound" | "trade_outbound" | "commute_outbound";

export interface BlocTotal {
  node_id: string;
  label: string;
  phi_inflow: number;
  trade: number;
  erdi_ratio: number;
}

export interface FlowTypeTotal {
  flow_type: FlowType;
  total: number;
  tick_count: number;
}

export interface TradePanelPayload {
  tick: number;
  has_data: boolean;
  total_phi_inflow: number;
  total_trade: number;
  blocs: BlocTotal[];
  flow_types: FlowTypeTotal[];
}

// ---------------------------------------------------------------------------
// Empty-state constants (honest zeros when no data)
// ---------------------------------------------------------------------------

export const EMPTY_TRADE_FLOWS: TradeFlowsPayload = {
  tick: 0,
  has_data: false,
  blocs: [],
};

export const EMPTY_EXPOSURE: ExposurePayload = {
  county_fips: "",
  has_data: false,
  total_exposure: 0,
  breakdown: { total: 0, contributors: [] },
  citations: [],
};

export const EMPTY_TRADE_PANEL: TradePanelPayload = {
  tick: 0,
  has_data: false,
  total_phi_inflow: 0,
  total_trade: 0,
  blocs: [],
  flow_types: [],
};
