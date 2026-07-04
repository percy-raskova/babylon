/**
 * MapModeSelector — visible control for cycling the spec-070
 * political-topology map lens (stance/heat/habitability/faction/collapse).
 *
 * Distinct from `FramingSelector` (admin-level LOD) and the analytical
 * `LensId` bar elsewhere in the v2 UI — see spec-093 Assumptions.
 */

import { useMapStore } from "@/stores/mapStore";
import type { LensMode } from "@/components/map/mapLensLayers";

const MODE_OPTIONS: { mode: LensMode; label: string; tooltip: string }[] = [
  { mode: "stance", label: "STANCE", tooltip: "Colonial Stance + faction influence rings" },
  { mode: "heat", label: "HEAT", tooltip: "State attention / surveillance pressure" },
  { mode: "habitability", label: "HABITABILITY", tooltip: "Metabolic-rift biocapacity gradient" },
  { mode: "faction", label: "FACTION", tooltip: "Single-faction influence filter" },
  { mode: "collapse", label: "COLLAPSE", tooltip: "Collapse-moment contested territories" },
];

export function MapModeSelector() {
  const lensMode = useMapStore((s) => s.lensMode);
  const setLensMode = useMapStore((s) => s.setLensMode);

  return (
    <div
      className="flex items-center gap-0.5 rounded-md border border-wet-concrete bg-void p-0.5"
      data-testid="map-mode-selector"
    >
      <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-ash">Lens</span>
      {MODE_OPTIONS.map(({ mode, label, tooltip }) => (
        <button
          key={mode}
          title={tooltip}
          data-testid={`lens-mode-${mode}`}
          aria-pressed={lensMode === mode}
          onClick={() => setLensMode(mode)}
          className={`rounded px-2 py-1 text-[11px] font-mono font-medium transition-colors ${
            lensMode === mode
              ? "bg-gold text-void"
              : "text-silver hover:bg-dark-metal hover:text-gold"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
