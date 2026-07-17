/**
 * The diegetic market ticker (Program 23 Phase 2, ADR078).
 *
 * The dramatic-irony surface: a DOW-styled index and CNBC-cadence headline
 * derived deterministically from the same `/timeseries/` payload the
 * X-ray chart reads (`lib/scissors.ts` — fixed copy table, mechanical
 * selection, zero randomness). Lives INSIDE the Scissors tab; the
 * narration panel stays frozen-unwired per the standing owner ruling.
 * Dark (renders nothing) until the market axis first computes.
 */

import type { TimeseriesPayload } from "@/types/game";
import { deriveTickerState, latestMeltDrift, type TickerTone } from "@/lib/scissors";

const TONE_CLASS: Record<TickerTone, string> = {
  crash: "text-laser",
  euphoria: "text-rupture", // bronze-gold: the rally the substrate can't back
  rally: "text-rupture",
  slump: "text-ash",
  steady: "text-ash",
};

function meltCopy(drift: number): string {
  const pct = Math.abs(drift * 100).toFixed(1);
  return drift >= 0
    ? `MELT drift +${(drift * 100).toFixed(1)}% — $1 commands ${pct}% less labor than its value basis`
    : `MELT drift ${(drift * 100).toFixed(1)}% — $1 commands ${pct}% more labor than its value basis`;
}

export function MarketTicker({
  payload,
}: {
  payload: TimeseriesPayload;
}): React.JSX.Element | null {
  const ticker = deriveTickerState(payload);
  if (ticker === null) return null;
  const drift = latestMeltDrift(payload);

  return (
    <div
      data-testid="market-ticker"
      className="flex items-baseline justify-between gap-3 border-b border-rebar px-3 py-1"
    >
      <span className={`font-mono text-[12px] font-bold ${TONE_CLASS[ticker.tone]}`}>
        BSE {ticker.index.toLocaleString("en-US")}
      </span>
      <span
        data-testid="ticker-headline"
        className={`truncate font-mono text-[10px] uppercase tracking-wider ${TONE_CLASS[ticker.tone]}`}
      >
        {ticker.headline}
      </span>
      {drift !== null && (
        <span data-testid="melt-drift" className="shrink-0 font-mono text-[10px] text-shroud">
          {meltCopy(drift)}
        </span>
      )}
    </div>
  );
}
