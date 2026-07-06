/**
 * Color scale legend for the active map layer.
 *
 * When a spec-070 political-topology lens is active (lensMode !== "stance"
 * or any lens with balkanization data), the lens legend label is rendered
 * by `DeckGLMap.tsx` via `LensLayerResult.legendLabel` — this component
 * hides itself to avoid rendering stale/contradictory content.
 */

import { useMapStore } from "@/stores/mapStore";
import { getColorScale, rgbaToCss } from "@/theme/colors";

const LEGEND_STEPS = 8;

export function MapLegend() {
  const activeLayer = useMapStore((s) => s.activeLayer);
  const lensMode = useMapStore((s) => s.lensMode);
  const scale = getColorScale(activeLayer);

  if (lensMode !== "stance") {
    return null;
  }

  const stops = Array.from({ length: LEGEND_STEPS }, (_, i) => {
    const t = i / (LEGEND_STEPS - 1);
    return { t, color: rgbaToCss(scale(t)) };
  });

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-ash">0</span>
      <div className="flex h-3 w-32 overflow-hidden rounded-sm">
        {stops.map((stop, i) => (
          <div key={i} className="flex-1" style={{ backgroundColor: stop.color }} />
        ))}
      </div>
      <span className="text-[10px] text-ash">1</span>
      <span className="text-[10px] uppercase tracking-wider text-ash">{activeLayer}</span>
    </div>
  );
}
