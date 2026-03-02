/**
 * Tooltip shown when hovering over a hex cell on the map.
 */

import type { TerritoryState } from "@/types/game";

interface HexTooltipProps {
  territory: TerritoryState;
  x: number;
  y: number;
}

export function HexTooltip({ territory, x, y }: HexTooltipProps) {
  return (
    <div
      className="pointer-events-none absolute z-50 min-w-[200px] rounded-md border border-wet-concrete bg-dark-metal p-3 text-xs shadow-lg"
      style={{ left: x + 12, top: y + 12 }}
    >
      <div className="mb-2 text-sm font-semibold text-bone">
        {territory.name}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <Stat label="Heat" value={territory.heat.toFixed(2)} />
        <Stat label="Rent" value={territory.rent_level.toFixed(2)} />
        <Stat label="Population" value={territory.population.toLocaleString()} />
        <Stat label="Sector" value={territory.sector_type} />
        <Stat label="Profile" value={territory.profile} />
        <Stat label="Biocapacity" value={territory.biocapacity.toFixed(2)} />
        {territory.under_eviction && (
          <span className="col-span-2 mt-1 text-[11px] font-bold uppercase text-phosphor-red">
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
