/**
 * Color scale legend for the active map layer.
 */

import { useMapStore } from "@/stores/mapStore";
import { getColorScale, rgbaToCss } from "@/theme/colors";

const LEGEND_STEPS = 8;

export function MapLegend() {
  const activeLayer = useMapStore((s) => s.activeLayer);
  const scale = getColorScale(activeLayer);

  const stops = Array.from({ length: LEGEND_STEPS }, (_, i) => {
    const t = i / (LEGEND_STEPS - 1);
    return { t, color: rgbaToCss(scale(t)) };
  });

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-ash">0</span>
      <div className="flex h-3 w-32 overflow-hidden rounded-sm">
        {stops.map((stop, i) => (
          <div
            key={i}
            className="flex-1"
            style={{ backgroundColor: stop.color }}
          />
        ))}
      </div>
      <span className="text-[10px] text-ash">1</span>
      <span className="text-[10px] uppercase tracking-wider text-ash">
        {activeLayer}
      </span>
    </div>
  );
}
