/**
 * Layer selector and opacity slider for the hex map.
 */

import { useMapStore } from "@/stores/mapStore";
import type { MapLayer } from "@/types/game";

const LAYERS: { id: MapLayer; label: string }[] = [
  { id: "heat", label: "Heat" },
  { id: "consciousness", label: "Consciousness" },
  { id: "wealth", label: "Wealth" },
  { id: "rent", label: "Rent" },
  { id: "biocapacity", label: "Biocapacity" },
  { id: "population", label: "Population" },
];

export function LayerControls() {
  const activeLayer = useMapStore((s) => s.activeLayer);
  const setActiveLayer = useMapStore((s) => s.setActiveLayer);
  const layerOpacity = useMapStore((s) => s.layerOpacity);
  const setLayerOpacity = useMapStore((s) => s.setLayerOpacity);
  const showEdges = useMapStore((s) => s.showEdges);
  const toggleEdges = useMapStore((s) => s.toggleEdges);

  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] uppercase tracking-wider text-ash">Layer:</span>
      {LAYERS.map((layer) => (
        <button
          key={layer.id}
          onClick={() => setActiveLayer(layer.id)}
          className={`rounded px-2 py-0.5 text-[11px] ${
            activeLayer === layer.id ? "bg-dark-metal text-gold" : "text-ash hover:text-silver"
          }`}
        >
          {layer.label}
        </button>
      ))}
      <div className="mx-2 h-4 w-px bg-wet-concrete" />
      <label className="flex items-center gap-1.5 text-[10px] text-ash">
        Opacity
        <input
          type="range"
          min={0}
          max={100}
          value={Math.round(layerOpacity * 100)}
          onChange={(e) => setLayerOpacity(Number(e.target.value) / 100)}
          className="h-1 w-16 appearance-none rounded bg-wet-concrete [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-gold"
        />
      </label>
      <button
        onClick={toggleEdges}
        className={`rounded px-2 py-0.5 text-[11px] ${
          showEdges ? "bg-dark-metal text-data-green" : "text-ash hover:text-silver"
        }`}
      >
        Edges
      </button>
    </div>
  );
}
