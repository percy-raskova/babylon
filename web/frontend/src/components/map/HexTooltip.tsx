/**
 * Tooltip shown when hovering over a hex cell on the map.
 * Metrics prioritized by active lens via inspectorPriority.
 */

import { useUIStore } from "@/stores/uiStore";
import { getLensById } from "@/lib/lensDefinitions";
import type { TerritoryState } from "@/types/game";

interface HexTooltipProps {
  territory: TerritoryState;
  x: number;
  y: number;
}

/** Lens-prioritized territory metric extraction. */
const TERRITORY_METRICS: Record<string, (t: TerritoryState) => string> = {
  heat: (t) => t.heat.toFixed(2),
  rent_level: (t) => t.rent_level.toFixed(2),
  population: (t) => t.population.toLocaleString(),
  biocapacity: (t) => t.biocapacity.toFixed(2),
  sector_type: (t) => t.sector_type,
  profile: (t) => t.profile,
  territory_type: (t) => t.territory_type,
};

/** All available metrics with display labels. */
const METRIC_LABELS: Record<string, string> = {
  heat: "Heat",
  rent_level: "Rent",
  population: "Population",
  biocapacity: "Biocapacity",
  sector_type: "Sector",
  profile: "Profile",
  territory_type: "Type",
};

/** Lens-specific priority ordering for tooltip metrics. */
const LENS_METRIC_PRIORITY: Record<string, string[]> = {
  economic: ["rent_level", "population", "biocapacity", "heat", "sector_type", "profile"],
  political: ["heat", "rent_level", "population", "profile", "biocapacity", "sector_type"],
  social: ["population", "heat", "biocapacity", "rent_level", "profile", "sector_type"],
  strategic: ["heat", "profile", "rent_level", "population", "biocapacity", "sector_type"],
};

/** Max metrics shown in tooltip. */
const MAX_TOOLTIP_METRICS = 6;

export function HexTooltip({ territory, x, y }: HexTooltipProps) {
  const activeLens = useUIStore((s) => s.activeLens);
  const lens = getLensById(activeLens);
  const fallback = ["heat", "rent_level", "population", "profile", "biocapacity", "sector_type"];
  const metricOrder = LENS_METRIC_PRIORITY[lens.id] ?? fallback;
  const visibleMetrics = metricOrder.slice(0, MAX_TOOLTIP_METRICS);

  return (
    <div
      className="pointer-events-none absolute z-50 min-w-[200px] rounded-md border border-wet-concrete bg-dark-metal p-3 text-xs shadow-lg"
      style={{ left: x + 12, top: y + 12 }}
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-bone">{territory.name}</span>
        <span className="rounded bg-soot px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-ash">
          {lens.name}
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
          <span className="col-span-2 mt-1 rounded bg-crimson/10 px-1 py-0.5 text-[11px] font-bold uppercase text-crimson">
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
      <span className="text-ash">{label}</span>
      <span className="font-mono text-bone">{value}</span>
    </>
  );
}
