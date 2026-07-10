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
