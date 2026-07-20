/**
 * MeltGauge — a real gauge instrument on the MELT drift already computed by
 * `latestMeltDrift` (Track 2 / T2-4, spec-117). Today MELT exists only as
 * one line of ticker text (`MarketTicker.tsx`'s `melt-drift` span); this
 * renders the SAME derivation as a needle-on-axis instrument, following the
 * `BifurcationGauge` SVG-axis convention exactly (axis line + center tick +
 * end labels + a needle positioned by value). Does not reimplement the
 * derivation — `latestMeltDrift`/`meltCopy` are both reused verbatim from
 * `lib/scissors.ts`.
 *
 * Passive read: takes `payload` as a prop rather than fetching its own copy.
 * The Circuit screen already mounts `ScissorsChart` alongside this gauge,
 * which drives the one `panels.timeseries` fetch both read — the same
 * "passive read of panels.timeseries" contract `BifurcationGauge`'s history
 * sparkline follows.
 */

import { latestMeltDrift, meltCopy } from "@/lib/scissors";
import { sparklinePoints } from "@/components/chrome/sparkline";
import type { TimeseriesPayload } from "@/types/game";

interface MeltGaugeProps {
  payload: TimeseriesPayload | null;
}

const AXIS_W = 176;
const AXIS_PAD = 12;
const AXIS_Y = 24;
/** Clamp domain: +/-50% drift maps onto the axis's drawable ends. */
const DRIFT_DOMAIN = 0.5;

/** Map a drift value onto the axis's pixel x-range, clamped to the domain. */
function needleX(drift: number): number {
  const clamped = Math.max(-DRIFT_DOMAIN, Math.min(DRIFT_DOMAIN, drift));
  return AXIS_PAD + ((clamped + DRIFT_DOMAIN) / (2 * DRIFT_DOMAIN)) * (AXIS_W - 2 * AXIS_PAD);
}

/**
 * The MELT gauge, or `null` when there is no payload yet or the MELT axis
 * has never computed (Constitution III.11 — a dark instrument, never a
 * fabricated zero reading).
 */
export function MeltGauge({ payload }: MeltGaugeProps): React.JSX.Element | null {
  if (payload === null) return null;
  const drift = latestMeltDrift(payload);
  if (drift === null) return null;

  const history = sparklinePoints(payload.price_index ?? [], AXIS_W, 16);
  const needleColor = drift >= 0 ? "var(--babylon-heat)" : "var(--babylon-solidarity)";

  return (
    <div className="flex flex-col gap-1 p-2" data-testid="melt-gauge">
      <p className="text-[9px] uppercase tracking-widest text-ksbc-muted-2">MELT Drift</p>
      <svg
        width={AXIS_W}
        height={40}
        className="block"
        data-testid="melt-gauge-axis"
        role="img"
        aria-label="MELT drift axis: a dollar commands more labor (left) to less labor (right)"
      >
        <line
          x1={AXIS_PAD}
          y1={AXIS_Y}
          x2={AXIS_W - AXIS_PAD}
          y2={AXIS_Y}
          stroke="var(--babylon-shroud)"
          strokeWidth="1"
        />
        <line
          x1={AXIS_W / 2}
          y1={AXIS_Y - 4}
          x2={AXIS_W / 2}
          y2={AXIS_Y + 4}
          stroke="var(--babylon-shroud)"
          strokeWidth="1"
        />
        <text x={AXIS_PAD - 2} y={9} className="text-[8px]" fill="var(--babylon-solidarity)">
          MORE
        </text>
        <text x={AXIS_W - AXIS_PAD - 24} y={9} className="text-[8px]" fill="var(--babylon-heat)">
          LESS
        </text>
        <circle
          data-testid="melt-gauge-needle"
          cx={needleX(drift)}
          cy={AXIS_Y}
          r={4}
          fill={needleColor}
        />
      </svg>
      {history !== null && (
        <svg
          width={AXIS_W}
          height={16}
          className="block"
          data-testid="melt-gauge-sparkline"
          role="img"
          aria-label="MELT drift trajectory history"
        >
          <polyline points={history} fill="none" stroke="var(--babylon-spire)" strokeWidth="1" />
        </svg>
      )}
      <p className="text-[9px] text-ksbc-muted-2" data-testid="melt-gauge-line">
        {meltCopy(drift)}
      </p>
    </div>
  );
}
