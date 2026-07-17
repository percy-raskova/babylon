/**
 * Pure derivations for the Scissors tab (Program 23 Phase 2, ADR078).
 *
 * Everything here is deterministic arithmetic over the `/timeseries/`
 * payload — no fetches, no randomness, no clock. The diegetic ticker's
 * headlines are a FIXED copy table selected by market state (the dramatic
 * irony is authored, the selection is mechanical): the surface celebrates
 * the rally while the X-ray chart below shows the scissors opening.
 */

import type { TimeseriesPayload } from "@/types/game";

/**
 * Ticks at which the cumulative correction count increments — the snap
 * ticks the chart marks. A null entry (axis absent) carries the previous
 * count forward; a pre-Phase-2 payload without the array yields [].
 */
export function deriveCorrectionTicks(payload: TimeseriesPayload): number[] {
  const counts = payload.market_corrections ?? [];
  const ticks: number[] = [];
  let previous = 0;
  for (let i = 0; i < counts.length; i += 1) {
    const count = counts[i];
    if (count === null || count === undefined) continue;
    if (count > previous) ticks.push(payload.ticks[i] ?? i);
    previous = count;
  }
  return ticks;
}

/**
 * Latest MELT drift: `price_index − 1` at the last non-null reading.
 * Positive = a dollar commands LESS labor than its value basis (the money
 * form has inflated against socially necessary labor time); null = the
 * axis has never computed.
 */
export function latestMeltDrift(payload: TimeseriesPayload): number | null {
  const series = payload.price_index ?? [];
  for (let i = series.length - 1; i >= 0; i -= 1) {
    const value = series[i];
    if (value !== null && value !== undefined) return value - 1;
  }
  return null;
}

export type TickerTone = "crash" | "euphoria" | "rally" | "slump" | "steady";

export interface TickerState {
  /** DOW-styled index number: round(10000 × fictitious_ratio). */
  index: number;
  tone: TickerTone;
  headline: string;
}

/** The authored copy table — CNBC cadence on top, the law of value below. */
const HEADLINES: Record<TickerTone, string> = {
  crash: "THE SCISSORS SNAP — TRILLIONS IN PAPER VALUE EVAPORATE",
  euphoria: "RECORDS AGAIN — ANALYSTS AGREE THIS TIME IS DIFFERENT",
  rally: "MARKETS SURGE ON STRONG EARNINGS MOMENTUM",
  slump: "STOCKS DRIFT LOWER — FUNDAMENTALS BLAMED",
  steady: "MARKETS FLAT AS INVESTORS AWAIT DIRECTION",
};

function lastTwoNonNull(series: (number | null | undefined)[]): [number, number] | null {
  const found: number[] = [];
  for (let i = series.length - 1; i >= 0 && found.length < 2; i -= 1) {
    const value = series[i];
    if (value !== null && value !== undefined) found.push(value);
  }
  const latest = found[0];
  if (latest === undefined) return null;
  return [found[1] ?? latest, latest];
}

/**
 * Deterministic ticker state from the latest payload readings, or null
 * when the market axis has never computed (the ticker stays dark — a
 * phenomenal form cannot precede its substance).
 */
export function deriveTickerState(payload: TimeseriesPayload): TickerState | null {
  const pair = lastTwoNonNull(payload.fictitious_ratio ?? []);
  if (pair === null) return null;
  const [previous, latest] = pair;
  const index = Math.round(10000 * latest);
  const corrections = deriveCorrectionTicks(payload);
  const lastTick = payload.ticks[payload.ticks.length - 1];
  const drift = latestMeltDrift(payload);

  let tone: TickerTone = "steady";
  if (corrections.length > 0 && corrections[corrections.length - 1] === lastTick) {
    tone = "crash";
  } else if (latest >= 1.3) {
    tone = "euphoria";
  } else if (latest > previous * 1.005) {
    tone = "rally";
  } else if (drift !== null && drift <= -0.05) {
    tone = "slump";
  }
  return { index, tone, headline: HEADLINES[tone] };
}
