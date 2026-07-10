/**
 * BlocFlowLines — per-bloc price/flow lines for the Wire INDEX tab.
 * Spec 103 FR-103-10: renders one row per external bloc with a Φ-inflow
 * sparkline, trade-value sparkline, and erdi_ratio. Uses Cold Collapse tokens.
 */

import { useTradeFlows } from "@/hooks/useTradeFlows";
import { Sparkline } from "@/components/bbl";
import "@/components/takeovers/wire/bloc-flow.css";

interface Props {
  gameId: string | null;
}

export function BlocFlowLines({ gameId }: Props) {
  const { data, loading, error } = useTradeFlows(gameId);

  if (loading && data.blocs.length === 0) {
    return (
      <div className="bloc-flow-loading" style={{ color: "var(--babylon-ash)" }}>
        Loading bloc flows...
      </div>
    );
  }
  if (error) {
    return (
      <div className="bloc-flow-error" style={{ color: "var(--babylon-laser)" }}>
        Bloc flows error: {error}
      </div>
    );
  }
  if (!data.has_data || data.blocs.length === 0) {
    return (
      <div className="bloc-flow-empty" style={{ color: "var(--babylon-fog)" }}>
        No boundary flows yet — trade lines populate when the engine emits DRAIN_EDGE rows.
      </div>
    );
  }

  return (
    <div className="bloc-flow-section">
      <div className="bloc-flow-header">
        <span className="wire-label">{"\u25b8"} Bloc Flows</span>
        <span
          className="text-[9px]"
          style={{
            color: "var(--babylon-fog)",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.16em",
          }}
        >
          {data.blocs.length} BLOCS · t={String(data.tick).padStart(4, "0")}
        </span>
      </div>
      <div className="bloc-flow-grid">
        {data.blocs.map((bloc) => (
          <div key={bloc.node_id} className="bloc-flow-row">
            <div className="bloc-flow-label">
              <span style={{ color: "var(--babylon-bone)" }}>{bloc.label}</span>
              {bloc.kind === "domestic_rest" && (
                <span className="text-[8px]" style={{ color: "var(--babylon-fog)" }}>
                  DOM
                </span>
              )}
            </div>
            <div className="bloc-flow-spark">
              <Sparkline
                data={bloc.phi_series.map((p) => p.magnitude)}
                color="var(--babylon-spire)"
                w={80}
                h={20}
                label="Φ"
                value={bloc.latest.phi_year_inflow}
              />
            </div>
            <div className="bloc-flow-spark">
              <Sparkline
                data={bloc.trade_series.map((p) => p.magnitude)}
                color="var(--babylon-cadre)"
                w={80}
                h={20}
                label="TRD"
                value={bloc.latest.bilateral_trade_value}
              />
            </div>
            <div className="bloc-flow-ratio">
              <span className="wire-label">ERDI</span>
              <span
                className="text-[12px] font-bold"
                style={{
                  color:
                    bloc.latest.erdi_ratio > 1.2 ? "var(--babylon-laser)" : "var(--babylon-bone)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {bloc.latest.erdi_ratio.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
