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
import {
  MAP_SAFE_LEFT,
  MAP_SAFE_RIGHT,
  MAP_SAFE_TOP,
  MAP_SAFE_MAX_WIDTH_CSS,
} from "@/components/chrome/layout";
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
      {/* Legend cluster: pinned to the map-safe area's top-left corner
          (below the TopBar strip, right of the outliner rail). Offsets DERIVE
          from chrome/layout.ts — no hand-tuned magic numbers. */}
      <div
        className="absolute z-10 flex flex-col gap-2 border-2 border-ksbc-muted-1 bg-plate/85 p-2 shadow-[4px_4px_0_#000] backdrop-blur-sm"
        style={{ left: MAP_SAFE_LEFT, top: MAP_SAFE_TOP }}
      >
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

      {/* Lens/framing cluster: right-anchored at the right rail's clearance,
          but CAPPED at the safe-area width so the wrapping grouped lens bar
          (flex-wrap) can never extend left under the outliner rail — the
          structural fix for the Phase-V z-strata interception. All three
          values derive from chrome/layout.ts. */}
      <div
        className="absolute z-10 flex flex-col items-end gap-2"
        style={{ right: MAP_SAFE_RIGHT, top: MAP_SAFE_TOP, maxWidth: MAP_SAFE_MAX_WIDTH_CSS }}
      >
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
