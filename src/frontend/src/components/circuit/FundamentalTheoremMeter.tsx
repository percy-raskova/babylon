/**
 * FundamentalTheoremMeter — the Circuit screen's Wc vs Vc meter (Track 2 /
 * T2-6, spec-117).
 *
 * T2-6a promotes the per-class `imperial_rent_gap` already computed for the
 * inspector popup (`_social_class_inspector_fields`) to a graph-wide
 * reading: `wage_flow_total` (Sigma core wages paid, W_c) against
 * `value_produced` (Sigma value produced, V_c) — both already-fetched
 * `EconomyDashboardPayload` fields, paired here into one meter instead of
 * living as two separate `EconomyDashboard` stat chips.
 *
 * T2-6b adds the net-new per-region breakdown
 * (`imperial_rent_gap_by_region` — see `_imperial_rent_gap_by_region`'s
 * docstring for why this needs `ScaleAdjunction.aggregate_intensive`
 * population-share-weighting rather than a naive per-class average).
 *
 * Self-mounts `panels.economy` (setMounted+fetch on mount) exactly like
 * `EconomyDashboard.tsx` — the Circuit screen doesn't otherwise fetch that
 * panel, so this is what closes the loop for this screen.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import {
  deriveFundamentalTheoremReading,
  fundamentalTheoremNarrative,
  sortRegionsByGapDescending,
} from "@/lib/fundamentalTheorem";

interface FundamentalTheoremMeterProps {
  gameId: string;
}

const BAR_MAX_WIDTH = 160;

/** Bar pixel width for `value`, scaled against the larger of Wc/Vc (never zero-divide). */
function barWidth(value: number, maxMagnitude: number): number {
  if (maxMagnitude <= 0) return 0;
  return Math.min(1, Math.abs(value) / maxMagnitude) * BAR_MAX_WIDTH;
}

export function FundamentalTheoremMeter({
  gameId,
}: FundamentalTheoremMeterProps): React.JSX.Element {
  const data = useStore((s) => s.panels.economy.data);
  const loading = useStore((s) => s.panels.economy.loading);
  const error = useStore((s) => s.panels.economy.error);
  const fetchEconomy = useStore((s) => s.panels.economy.fetch);
  const setMounted = useStore((s) => s.panels.economy.setMounted);

  useEffect(() => {
    setMounted(true);
    void fetchEconomy(gameId);
    return () => setMounted(false);
  }, [gameId, fetchEconomy, setMounted]);

  if (loading && data === null) {
    return (
      <p className="p-2 text-[11px] text-ash" data-testid="fundamental-theorem-loading">
        Loading the Fundamental Theorem…
      </p>
    );
  }
  if (error) {
    return (
      <p role="alert" className="p-2 text-[11px] text-laser">
        {error}
      </p>
    );
  }
  if (data === null) {
    return <p className="p-2 text-[11px] italic text-shroud">No economy data yet.</p>;
  }

  const reading = deriveFundamentalTheoremReading(data);
  if (reading === null) {
    return (
      <p className="p-2 text-[11px] italic text-shroud" data-testid="fundamental-theorem-no-data">
        No economic activity recorded in this graph yet.
      </p>
    );
  }

  const maxMagnitude = Math.max(reading.wc, reading.vc, 1);
  const regions = sortRegionsByGapDescending(data.imperial_rent_gap_by_region);

  return (
    <div className="flex flex-col gap-2 p-2" data-testid="fundamental-theorem-meter">
      <p className="text-[9px] uppercase tracking-widest text-ksbc-muted-2">
        Fundamental Theorem — Wc vs Vc
      </p>
      <div className="flex flex-col gap-1" data-testid="fundamental-theorem-bars">
        <div className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-[9px] uppercase text-ksbc-muted-2">Core Wages</span>
          <div className="h-2 bg-rebar" style={{ width: BAR_MAX_WIDTH }}>
            <div
              className="h-2 bg-cadre"
              style={{ width: barWidth(reading.wc, maxMagnitude) }}
              data-testid="fundamental-theorem-wc-bar"
            />
          </div>
          <span className="font-mono text-[10px] text-bone">{reading.wc.toFixed(1)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-[9px] uppercase text-ksbc-muted-2">
            Value Produced
          </span>
          <div className="h-2 bg-rebar" style={{ width: BAR_MAX_WIDTH }}>
            <div
              className="h-2 bg-population"
              style={{ width: barWidth(reading.vc, maxMagnitude) }}
              data-testid="fundamental-theorem-vc-bar"
            />
          </div>
          <span className="font-mono text-[10px] text-bone">{reading.vc.toFixed(1)}</span>
        </div>
      </div>
      <p
        className={`text-[10px] ${reading.hasSubsidy ? "text-rupture" : "text-solidarity"}`}
        data-testid="fundamental-theorem-narrative"
      >
        {fundamentalTheoremNarrative(reading)}
      </p>
      <div>
        <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">By Region</p>
        {regions.length === 0 ? (
          <p
            className="text-[11px] italic text-shroud"
            data-testid="fundamental-theorem-regions-empty"
          >
            No region carries a positive-population tenant class yet.
          </p>
        ) : (
          <ul className="flex flex-col gap-0.5" data-testid="fundamental-theorem-regions">
            {regions.map((row) => (
              <li
                key={row.territory_id}
                data-testid={`fundamental-theorem-region-${row.territory_id}`}
                className="flex items-center justify-between text-[10px]"
              >
                <span className="text-bone">{row.territory_id}</span>
                <span className={row.gap_per_capita > 0 ? "text-rupture" : "text-solidarity"}>
                  {row.gap_per_capita.toFixed(3)} / capita
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
