/**
 * Color scale legend for the active map lens.
 *
 * Adapted (spec-110 B2) to a `lens: Lens` prop instead of reading
 * `mapStore.activeLayer`/`lensMode` — those two independent axes are now
 * one `Lens` value (`@/lib/lens`). Renders nothing for the three
 * balkanization-derived lenses (stance/faction/collapse): their fill is a
 * discrete per-faction stance color, not a continuous ramp, so
 * `lensRampStops` returns `null` for them and there's nothing to draw a
 * swatch strip for — `DeckGLMap`'s `lensResult.legendLabel` text already
 * covers those.
 */

import { lensLegendLabel, lensRampStops, sampleRampStops, type Lens } from "@/lib/lens";
import { rgbaToCss } from "@/theme/colors";

const LEGEND_STEPS = 8;

interface MapLegendProps {
  lens: Lens;
}

export function MapLegend({ lens }: MapLegendProps) {
  const stops = lensRampStops(lens);
  if (!stops) return null;

  const swatches = Array.from({ length: LEGEND_STEPS }, (_, i) => {
    const t = i / (LEGEND_STEPS - 1);
    return { t, color: rgbaToCss(sampleRampStops(stops, t)) };
  });

  return (
    <div className="flex items-center gap-2" data-testid="map-legend">
      <span className="text-[10px] text-ash">0</span>
      <div className="flex h-3 w-32 overflow-hidden rounded-sm">
        {swatches.map((swatch, i) => (
          <div key={i} className="flex-1" style={{ backgroundColor: swatch.color }} />
        ))}
      </div>
      <span className="text-[10px] text-ash">1</span>
      <span className="text-[10px] uppercase tracking-wider text-ash">{lensLegendLabel(lens)}</span>
    </div>
  );
}
