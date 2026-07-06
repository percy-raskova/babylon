/**
 * TradePanel — aggregate trade panel for the Analysis page.
 * Spec 103 FR-103-12: renders total Φ inflow, per-bloc bars, and flow-type
 * summary. Uses Cold Collapse tokens.
 */

import type { ReactNode } from "react";
import { BblBadge, BblLabel, BblPanel, Stat } from "@/components/bbl";
import { useTradePanel } from "@/hooks/useTradePanel";
import "@/components/pages/trade-panel.css";

interface Props {
  gameId: string | null;
}

const FLOW_TYPE_LABELS: Record<string, string> = {
  drain_edge: "DRAIN (Φ)",
  trade_inbound: "TRADE IN",
  trade_outbound: "TRADE OUT",
  commute_outbound: "COMMUTE OUT",
};

export function TradePanel({ gameId }: Props) {
  const { data, loading, error } = useTradePanel(gameId);

  const maxPhi = data.blocs.length > 0 ? Math.max(...data.blocs.map((b) => b.phi_inflow), 1) : 1;

  let body: ReactNode;
  if (loading && !data.has_data) {
    body = <div className="text-[11px] text-ash">Loading trade panel...</div>;
  } else if (error) {
    body = (
      <div className="text-[11px]" style={{ color: "var(--babylon-laser)" }}>
        Error: {error}
      </div>
    );
  } else if (!data.has_data) {
    body = (
      <div className="text-[11px] text-ash">
        No boundary flows yet. Trade aggregates populate when the engine emits DRAIN_EDGE /
        TRADE_EDGE rows.
      </div>
    );
  } else {
    body = (
      <div className="trade-panel-body">
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Total Φ Inflow" value={data.total_phi_inflow.toFixed(1)} color="#5fbf7a" />
          <Stat label="Total Trade" value={data.total_trade.toFixed(1)} color="#c8a860" />
        </div>

        <BblLabel color="#80b0e0">Per-Bloc Φ Inflow</BblLabel>
        <div className="trade-bar-list">
          {data.blocs.map((bloc) => (
            <div key={bloc.node_id} className="trade-bar-row">
              <span className="trade-bar-label">{bloc.label}</span>
              <div className="trade-bar-track">
                <div
                  className="trade-bar-fill"
                  style={{
                    width: `${(bloc.phi_inflow / maxPhi) * 100}%`,
                    background: "var(--babylon-solidarity, #40c040)",
                  }}
                />
              </div>
              <span className="trade-bar-value" style={{ fontFamily: "var(--font-mono)" }}>
                {bloc.phi_inflow.toFixed(1)}
              </span>
              <span className="trade-bar-ratio" style={{ fontFamily: "var(--font-mono)" }}>
                erdi={bloc.erdi_ratio.toFixed(2)}
              </span>
            </div>
          ))}
        </div>

        <BblLabel color="#787878">Flow Types</BblLabel>
        <div className="trade-flowtype-list">
          {data.flow_types.map((ft) => (
            <div key={ft.flow_type} className="trade-flowtype-row">
              <span className="trade-flowtype-label">
                {FLOW_TYPE_LABELS[ft.flow_type] ?? ft.flow_type}
              </span>
              <span className="trade-flowtype-value" style={{ fontFamily: "var(--font-mono)" }}>
                {ft.total.toFixed(1)}
              </span>
              <span className="trade-flowtype-ticks text-[9px] text-ash">
                {ft.tick_count} ticks
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <BblPanel
      title="Trade Flows"
      right={
        data.has_data ? (
          <BblBadge color="#5fbf7a">t={data.tick}</BblBadge>
        ) : (
          <BblBadge color="#787878">no data</BblBadge>
        )
      }
    >
      {body}
    </BblPanel>
  );
}
