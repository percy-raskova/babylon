/**
 * Hex map visualization.
 *
 * Renders territory data as colored hex cells in a grid.
 * Hex color encodes a selectable metric (heat, consciousness, wealth).
 */

import { useCallback, useMemo, useState } from "react";
import type { GameSnapshot, TerritoryState, MapLayer } from "@/types/game";

/** Color scales for different metrics. */
const COLOR_SCALES: Record<string, (v: number) => string> = {
  heat: (v) => {
    const r = Math.round(40 + v * 200);
    const g = Math.round(40 - v * 30);
    const b = Math.round(60 - v * 40);
    return `rgb(${r},${g},${b})`;
  },
  consciousness: (v) => {
    const r = Math.round(40 + v * 60);
    const g = Math.round(60 + v * 140);
    const b = Math.round(100 + v * 150);
    return `rgb(${r},${g},${b})`;
  },
  wealth: (v) => {
    const r = Math.round(50 + v * 150);
    const g = Math.round(160 + v * 80);
    const b = Math.round(50 + v * 50);
    return `rgb(${r},${g},${b})`;
  },
  rent: (v) => {
    const r = Math.round(60 + v * 180);
    const g = Math.round(40 + v * 40);
    const b = Math.round(80 + v * 100);
    return `rgb(${r},${g},${b})`;
  },
  biocapacity: (v) => {
    const r = Math.round(30 + v * 30);
    const g = Math.round(80 + v * 160);
    const b = Math.round(40 + v * 60);
    return `rgb(${r},${g},${b})`;
  },
  population: (v) => {
    const r = Math.round(60 + v * 120);
    const g = Math.round(60 + v * 100);
    const b = Math.round(120 + v * 130);
    return `rgb(${r},${g},${b})`;
  },
};

/** Extract the numeric metric value from a territory. */
function getMetricValue(territory: TerritoryState, metric: MapLayer): number {
  switch (metric) {
    case "heat":
      return territory.heat;
    case "consciousness":
      return 0; // Territories don't have consciousness — needs entity overlay
    case "wealth":
      return territory.rent_level;
    case "rent":
      return territory.rent_level;
    case "biocapacity":
      return territory.biocapacity;
    case "population":
      return Math.min(territory.population / 1_000_000, 1); // Normalize
  }
}

interface HexMapProps {
  snapshot: GameSnapshot;
  onSelectNode?: (nodeId: string) => void;
}

export function HexMap({ snapshot, onSelectNode }: HexMapProps) {
  const [metric, setMetric] = useState<MapLayer>("heat");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const territories = snapshot.territories;

  const getColor = useCallback(
    (territory: TerritoryState) => {
      const value = getMetricValue(territory, metric);
      const clamped = Math.max(0, Math.min(1, value));
      const scale = COLOR_SCALES[metric] ?? COLOR_SCALES["heat"]!;
      return scale(clamped);
    },
    [metric],
  );

  const hoveredTerritory = useMemo(() => {
    if (!hoveredId) return null;
    return territories.find((t) => t.id === hoveredId) ?? null;
  }, [hoveredId, territories]);

  return (
    <div className="relative flex h-full flex-col">
      {/* Layer controls */}
      <div className="flex shrink-0 items-center gap-2 py-2">
        <span className="text-xs uppercase tracking-wider text-ash">Color by:</span>
        {Object.keys(COLOR_SCALES).map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m as MapLayer)}
            className={`rounded border px-2.5 py-1 text-xs ${
              metric === m
                ? "border-gold bg-[#1a1a30] text-gold"
                : "border-wet-concrete bg-void text-ash hover:border-silver"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Grid-based hex display (deck.gl integration in Phase 3) */}
      <div className="grid flex-1 grid-cols-[repeat(auto-fill,minmax(80px,1fr))] gap-1 overflow-auto py-2">
        {territories.map((territory) => (
          <button
            key={territory.id}
            onClick={() => onSelectNode?.(territory.id)}
            onMouseEnter={() => setHoveredId(territory.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={`flex aspect-square min-h-[60px] items-center justify-center rounded-md transition-[border] duration-150 ${
              hoveredId === territory.id ? "border-2 border-gold" : "border border-soot"
            }`}
            style={{ background: getColor(territory) }}
            title={`${territory.name}: ${metric}=${getMetricValue(territory, metric).toFixed(2)}`}
          >
            <span className="break-all text-center text-[10px] text-white/70">
              {territory.name.slice(0, 8)}
            </span>
          </button>
        ))}
        {territories.length === 0 && (
          <p className="col-span-full py-8 text-center text-sm text-ash">
            No territory data available
          </p>
        )}
      </div>

      {/* Hover tooltip */}
      {hoveredTerritory && (
        <div className="absolute inset-x-2 bottom-2 max-h-[200px] overflow-auto rounded-md border border-wet-concrete bg-dark-metal p-2.5 text-xs text-silver">
          <strong className="text-bone">{hoveredTerritory.name}</strong>
          <pre className="mt-1 whitespace-pre-wrap text-[11px] text-ash">
            {JSON.stringify(hoveredTerritory, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
