/**
 * Tooltip shown when hovering over a hex cell on the map.
 * Metrics prioritized by the active `Lens`.
 *
 * Adapted (spec-110 B2) to take `lens: Lens` as a prop rather than reading
 * `uiStore.activeLens` + `lib/lensDefinitions.ts`'s `LensId`-keyed priority
 * table. That analytical-lens concept (`economic`/`political`/`social`/
 * `strategic`) is a third axis distinct from the map lens this lane
 * unifies — see spec-110 B2's report for why it's out of scope here. The
 * priority table below is keyed on the new `Lens["kind"]`/`MapMetric`
 * instead, so the tooltip still emphasizes metrics relevant to whatever's
 * actually painted on the map.
 */

import type { Lens } from "@/lib/lens";
import type { TerritoryState } from "@/types/game";

interface HexTooltipProps {
  territory: TerritoryState;
  x: number;
  y: number;
  lens: Lens;
}

/** Metric extraction, keyed by the same names used in priority lists below. */
const TERRITORY_METRICS: Record<string, (t: TerritoryState) => string> = {
  heat: (t) => t.heat.toFixed(2),
  rent_level: (t) => t.rent_level.toFixed(2),
  population: (t) => t.population.toLocaleString(),
  biocapacity: (t) => t.biocapacity.toFixed(2),
  habitability: (t) => (t.habitability != null ? t.habitability.toFixed(2) : "—"),
  sector_type: (t) => t.sector_type,
  profile: (t) => t.profile,
  territory_type: (t) => t.territory_type,
  // Wave 5 receptivity pair — em-dash for honest absence (a tenant-less
  // territory or a never-stepped graph; Constitution III.11), never a
  // fabricated 0. intel_confidence rides here too (its ONLY map surface —
  // no lens; uniformly 0.1 today, see the program report).
  mass_receptivity: (t) => (t.mass_receptivity != null ? t.mass_receptivity.toFixed(2) : "—"),
  intel_confidence: (t) => (t.intel_confidence != null ? t.intel_confidence.toFixed(2) : "—"),
  vision_state: (t) => t.vision_state ?? "—",
  // Feature 021 lens pair — em-dash for honest absence (the writing system
  // found no reserve-army pressure / no dispossession activity this tick;
  // Constitution III.11), never a fabricated 0.
  wage_pressure: (t) => (t.wage_pressure != null ? t.wage_pressure.toFixed(2) : "—"),
  dispossession_intensity: (t) =>
    t.dispossession_intensity != null ? t.dispossession_intensity.toFixed(2) : "—",
};

const METRIC_LABELS: Record<string, string> = {
  heat: "Heat",
  rent_level: "Rent",
  population: "Population",
  biocapacity: "Biocapacity",
  habitability: "Habitability",
  sector_type: "Sector",
  profile: "Profile",
  territory_type: "Type",
  mass_receptivity: "Receptivity",
  intel_confidence: "Intel",
  vision_state: "Vision",
  wage_pressure: "Wage Pressure",
  dispossession_intensity: "Dispossession",
};

const DEFAULT_PRIORITY = [
  "heat",
  "rent_level",
  "population",
  "profile",
  "biocapacity",
  "sector_type",
];

/** Priority ordering for tooltip metrics, keyed by Lens kind (or "metric:<name>"). */
const LENS_METRIC_PRIORITY: Record<string, string[]> = {
  stance: ["rent_level", "population", "sector_type", "heat", "profile", "biocapacity"],
  heat: ["heat", "rent_level", "population", "profile", "biocapacity", "sector_type"],
  habitability: ["habitability", "biocapacity", "heat", "population", "rent_level", "profile"],
  faction: DEFAULT_PRIORITY,
  collapse: ["heat", "profile", "rent_level", "population", "biocapacity", "sector_type"],
  "metric:profit_rate": [
    "rent_level",
    "population",
    "biocapacity",
    "heat",
    "profile",
    "sector_type",
  ],
  "metric:population": [
    "population",
    "heat",
    "biocapacity",
    "rent_level",
    "profile",
    "sector_type",
  ],
  // Wave 5 receptivity pair: both lenses lead with the receptivity trio
  // (M_r, its categorical cut, and intel_confidence — which has no lens of
  // its own and surfaces here), then fall back to the material base.
  "metric:mass_receptivity": [
    "mass_receptivity",
    "vision_state",
    "intel_confidence",
    "population",
    "heat",
    "rent_level",
  ],
  vision_state: [
    "vision_state",
    "mass_receptivity",
    "intel_confidence",
    "population",
    "heat",
    "rent_level",
  ],
  // Feature 021 lens pair: each lens leads with itself, then its sibling,
  // then falls back to the material base.
  "metric:wage_pressure": [
    "wage_pressure",
    "dispossession_intensity",
    "population",
    "heat",
    "rent_level",
    "biocapacity",
  ],
  "metric:dispossession_intensity": [
    "dispossession_intensity",
    "wage_pressure",
    "population",
    "heat",
    "rent_level",
    "biocapacity",
  ],
};

/** Max metrics shown in tooltip. */
const MAX_TOOLTIP_METRICS = 6;

function priorityKey(lens: Lens): string {
  return lens.kind === "metric" ? `metric:${lens.metric}` : lens.kind;
}

export function HexTooltip({ territory, x, y, lens }: HexTooltipProps) {
  const metricOrder = LENS_METRIC_PRIORITY[priorityKey(lens)] ?? DEFAULT_PRIORITY;
  const visibleMetrics = metricOrder.slice(0, MAX_TOOLTIP_METRICS);

  return (
    <div
      className="pointer-events-none absolute z-50 min-w-[200px] rounded-md border border-wet-steel bg-concrete p-3 text-xs shadow-lg"
      style={{ left: x + 12, top: y + 12 }}
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-bone">{territory.name}</span>
        <span className="rounded bg-rebar px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-ash">
          {priorityKey(lens)}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        {visibleMetrics.map((key) => {
          const extractor = TERRITORY_METRICS[key];
          const label = METRIC_LABELS[key];
          if (!extractor || !label) return null;
          return <Stat key={key} label={label} value={extractor(territory)} />;
        })}
        {territory.under_eviction && (
          <span className="col-span-2 mt-1 rounded bg-laser/10 px-1 py-0.5 text-[11px] font-bold uppercase text-laser">
            Under Eviction
          </span>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span className="text-ash" data-testid="hex-tooltip-stat-label">
        {label}
      </span>
      <span className="font-mono text-bone">{value}</span>
    </>
  );
}
