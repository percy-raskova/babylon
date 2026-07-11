/**
 * MapControls — composes `MapLensBar` + `MapLegend` + `FramingSelector`
 * into the map's floating control cluster (spec-113 Lane B, architecture
 * §3.3). `DeckGLMap.tsx` used to embed this cluster inline; it now sheds it
 * to this sibling component so `DeckGLMap` is pure canvas + tooltips (the
 * Lane A/Lane B interface architecture §3.3 names).
 */

import { MapLensBar } from "@/components/map/MapLensBar";
import { MapLegend } from "@/components/map/MapLegend";
import { FramingSelector } from "@/components/map/FramingSelector";
import { lensDefForLens, type LensAvailabilityContext } from "@/lib/lenses/registry";
import { lensLegendLabel, type Lens } from "@/lib/lens";
import type { FactionSummary } from "@/components/map/mapLensLayers";
import type { AdminLevel } from "@/types/game";

interface MapControlsProps {
  lens: Lens;
  onLensChange?: (lens: Lens) => void;
  factionFilter?: string | null;
  onFactionFilterChange?: (factionId: string | null) => void;
  factions?: FactionSummary[];
  framing: AdminLevel;
  onFramingChange?: (level: AdminLevel) => void;
  availability?: LensAvailabilityContext;
  /**
   * Ramp mode only: normalized [0,1] position of the current world-state
   * value on the active ramp (bible §3.2's Sylvester marker) — `null`/
   * omitted renders no marker (Constitution III.11: no fabricated position).
   */
  currentValue?: number | null;
  /** True for one render after the domain memo reports a would-be silent rescale. */
  flash?: boolean;
  /**
   * The honest per-tick legend status text `buildLensLayers` computes
   * (mode label/metric name, with a "— no data" suffix for an empty-but-
   * present balkanization block) — distinct from the registry's static
   * `MapLensDef.label`, and the `lens-legend-label` testid contract
   * `map-lens-cycling.spec.ts` pins. `null`/omitted renders nothing (mirrors
   * the pre-extraction `showLensLegendLabel` suppression).
   */
  legendStatusText?: string | null;
}

export function MapControls({
  lens,
  onLensChange,
  factionFilter,
  onFactionFilterChange,
  factions,
  framing,
  onFramingChange,
  availability = {},
  currentValue = null,
  flash = false,
  legendStatusText = null,
}: MapControlsProps) {
  const def = lensDefForLens(lens);
  const legend = def?.legend ?? { kind: "none" as const };
  const label = def?.label ?? lensLegendLabel(lens);

  return (
    <>
      <div className="absolute left-3 top-3 z-10 flex flex-col gap-2 border-2 border-ksbc-muted-1 bg-plate/85 p-2 shadow-[4px_4px_0_#000] backdrop-blur-sm">
        <MapLegend legend={legend} label={label} currentValue={currentValue} flash={flash} />
        {legendStatusText && (
          <span
            data-testid="lens-legend-label"
            className="text-[10px] uppercase tracking-wider text-ksbc-muted-2"
          >
            {legendStatusText}
          </span>
        )}
      </div>

      <div className="absolute right-3 top-3 z-10 flex flex-col items-end gap-2">
        <MapLensBar
          lens={lens}
          onLensChange={onLensChange}
          factionFilter={factionFilter}
          onFactionFilterChange={onFactionFilterChange}
          factions={factions}
          availability={availability}
        />
        <FramingSelector framing={framing} onFramingChange={onFramingChange} />
      </div>
    </>
  );
}
