/**
 * ObservatoryChart preview — pure presentational (points + metrics props;
 * no fetch, no store). One canonical determinism-trace-flavored
 * value-aggregate series for a Wayne County (FIPS 26163) session, ticks
 * 96-105 — shared across cells and sliced by `metrics`, mirroring how
 * SeriesBrowser actually drives this component (one fetched series, the
 * metric-toggle row picks which lines render).
 *
 * v_sum/s_sum is the Fundamental Theorem framing (CLAUDE.md §7): wages
 * (variable capital) vs. surplus — the widening gap is Imperial Rent Φ.
 * biocapacity_sum trends down tick-over-tick (metabolic-rift overshoot).
 * hex_count is deliberately its own cell rather than folded in with the
 * six-figure sums: the component has a single shared Y-axis (no
 * per-metric scale), so a ~1500x magnitude gap would flatten it into an
 * invisible line at the bottom — that's real behavior, not something to
 * paper over, but it belongs in learnings, not baked into a misleading cell.
 */
import { ObservatoryChart } from "babylon-cockpit";

const WAYNE_COUNTY_SERIES = [
  {
    tick: 96,
    v_sum: 482910.44,
    s_sum: 612340.18,
    c_sum: 891204.6,
    k_sum: 2184760.5,
    biocapacity_sum: 158204.77,
    hex_count: 142,
  },
  {
    tick: 97,
    v_sum: 483188.12,
    s_sum: 614890.55,
    c_sum: 891580.33,
    k_sum: 2186012.77,
    biocapacity_sum: 158010.22,
    hex_count: 142,
  },
  {
    tick: 98,
    v_sum: 483402.79,
    s_sum: 617310.02,
    c_sum: 891960.71,
    k_sum: 2187290.44,
    biocapacity_sum: 157809.65,
    hex_count: 142,
  },
  {
    tick: 99,
    v_sum: 483601.05,
    s_sum: 619872.41,
    c_sum: 892300.18,
    k_sum: 2188510.19,
    biocapacity_sum: 157602.14,
    hex_count: 142,
  },
  {
    tick: 100,
    v_sum: 483779.3,
    s_sum: 622401.77,
    c_sum: 892650.94,
    k_sum: 2189790.62,
    biocapacity_sum: 157388.9,
    hex_count: 143,
  },
  {
    tick: 101,
    v_sum: 483951.87,
    s_sum: 624955.3,
    c_sum: 892988.4,
    k_sum: 2191002.35,
    biocapacity_sum: 157169.33,
    hex_count: 143,
  },
  {
    tick: 102,
    v_sum: 484098.22,
    s_sum: 627502.88,
    c_sum: 893320.15,
    k_sum: 2192280.71,
    biocapacity_sum: 156943.78,
    hex_count: 143,
  },
  {
    tick: 103,
    v_sum: 484240.61,
    s_sum: 630018.14,
    c_sum: 893655.82,
    k_sum: 2193510.88,
    biocapacity_sum: 156712.05,
    hex_count: 144,
  },
  {
    tick: 104,
    v_sum: 484379.03,
    s_sum: 632544.69,
    c_sum: 893990.47,
    k_sum: 2194790.16,
    biocapacity_sum: 156474.61,
    hex_count: 144,
  },
  {
    tick: 105,
    v_sum: 484502.9,
    s_sum: 635091.23,
    c_sum: 894320.99,
    k_sum: 2196012.53,
    biocapacity_sum: 156231.09,
    hex_count: 144,
  },
];

// Inline pixel sizing, not Tailwind arbitrary-value classes (`w-[..]`/`h-[..]`):
// Tailwind v4's auto content-detection scans from src/frontend/ and never
// reaches .design-sync/previews/ (no `@source` override in index.css), so a
// class that doesn't ALSO appear somewhere in real app source silently
// compiles to nothing — confirmed empirically (these classes were entirely
// absent from ds-bundle/_ds_bundle.css). Recharts' ResponsiveContainer
// (height="100%") needs a real pixel height in its ancestor chain or it
// renders zero-size, so this can't be worked around by letting a block div's
// width auto-fill the way a plain list can. See learnings/observatory.md.
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void p-4" style={{ width: 760, height: 400 }}>
      {children as never}
    </div>
  );
}

export function WagesVsSurplus() {
  return (
    <Frame>
      <ObservatoryChart points={WAYNE_COUNTY_SERIES} metrics={["v_sum", "s_sum"]} />
    </Frame>
  );
}

export function CapitalStock() {
  return (
    <Frame>
      <ObservatoryChart points={WAYNE_COUNTY_SERIES} metrics={["k_sum"]} />
    </Frame>
  );
}

export function Biocapacity() {
  return (
    <Frame>
      <ObservatoryChart points={WAYNE_COUNTY_SERIES} metrics={["biocapacity_sum"]} />
    </Frame>
  );
}

export function HexCountTerritory() {
  return (
    <Frame>
      <ObservatoryChart points={WAYNE_COUNTY_SERIES} metrics={["hex_count"]} />
    </Frame>
  );
}

export function NoDataForScope() {
  return (
    <Frame>
      <ObservatoryChart points={[]} metrics={["v_sum", "s_sum"]} />
    </Frame>
  );
}
