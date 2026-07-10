/**
 * Trade flows — TypeScript types for the Wire INDEX tab's bloc-flow rows.
 *
 * Ported from `web/frontend/src/types/trade.ts` (spec 103); this cockpit
 * only consumes the trade-flows contract (the Wire family's
 * `BlocFlowLines`), not the exposure/trade-panel contracts, so only that
 * subset is ported here — surgical port, not a full-file copy.
 * Mirrors `specs/103-trade-surfaces/contracts/trade-flows.yaml`. Served by
 * a GET-only endpoint reading persisted engine state (Constitution III: AI
 * observes).
 */

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

/** Empty-state default (honest zeros when no data). */
export const EMPTY_TRADE_FLOWS: TradeFlowsPayload = {
  tick: 0,
  has_data: false,
  blocs: [],
};
