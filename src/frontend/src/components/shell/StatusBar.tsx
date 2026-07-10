/**
 * Top StatusBar — real `/summary/` fields (tick, profit rate, imperial
 * rent Φ, population, alert counts) plus the B4 transport controls.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { StatChip } from "./StatChip";
import { TimeControls } from "./TimeControls";

interface StatusBarProps {
  gameId: string;
}

export function StatusBar({ gameId }: StatusBarProps): React.JSX.Element {
  const tick = useStore((s) => s.world.snapshot?.tick);
  const summaryData = useStore((s) => s.panels.summary.data);
  const fetchSummary = useStore((s) => s.panels.summary.fetch);
  const setSummaryMounted = useStore((s) => s.panels.summary.setMounted);

  useEffect(() => {
    setSummaryMounted(true);
    void fetchSummary(gameId);
    return () => setSummaryMounted(false);
  }, [gameId, fetchSummary, setSummaryMounted]);

  const eventCounts = summaryData?.event_counts;
  const hasAlerts = eventCounts !== undefined && eventCounts.critical + eventCounts.warning > 0;

  return (
    <header
      data-testid="region-statusbar"
      aria-label="StatusBar"
      className="col-span-3 flex items-center justify-between border-b border-rebar px-4"
    >
      <div className="flex items-center gap-4">
        <span className="text-sm font-semibold tracking-[4px] text-spire">BABYLON COCKPIT</span>
        <div className="flex items-baseline gap-2 border-l border-rebar pl-4">
          <span className="text-[9px] uppercase tracking-widest text-ash">Tick</span>
          <span className="font-mono text-xl font-bold text-spire" data-testid="tick-value">
            {tick ?? "no data"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <StatChip
          label="Profit"
          value={summaryData?.profit_rate ?? null}
          format={(v) => v.toFixed(3)}
          colorClassName="text-rupture"
        />
        <StatChip
          label="Rent Φ"
          value={summaryData?.imperial_rent ?? null}
          format={(v) => v.toFixed(2)}
          colorClassName="text-rent"
        />
        <StatChip
          label="Pop"
          value={summaryData?.population_total ?? null}
          format={(v) => v.toLocaleString()}
          colorClassName="text-population"
        />
        {hasAlerts && (
          <div className="flex items-center gap-1" data-testid="alert-counts">
            {eventCounts.critical > 0 && (
              <span
                title={`${eventCounts.critical} critical events`}
                className="rounded-full bg-laser px-1.5 py-0.5 font-mono text-[10px] font-bold text-void"
              >
                {eventCounts.critical}
              </span>
            )}
            {eventCounts.warning > 0 && (
              <span
                title={`${eventCounts.warning} warning events`}
                className="rounded-full bg-heat px-1.5 py-0.5 font-mono text-[10px] font-bold text-void"
              >
                {eventCounts.warning}
              </span>
            )}
          </div>
        )}
      </div>

      <TimeControls gameId={gameId} />
    </header>
  );
}
