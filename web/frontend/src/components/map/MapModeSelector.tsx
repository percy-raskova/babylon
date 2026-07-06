/**
 * MapModeSelector — visible control for cycling the spec-070
 * political-topology map lens (stance/heat/habitability/faction/collapse).
 *
 * Distinct from `FramingSelector` (admin-level LOD) and the analytical
 * `LensId` bar elsewhere in the v2 UI — see spec-093 Assumptions.
 *
 * When the "faction" lens is active, shows a faction picker dropdown
 * sourced from the balkanization block's faction list (FR-025).
 */

import { useMapStore } from "@/stores/mapStore";
import type { LensMode, FactionSummary } from "@/components/map/mapLensLayers";

const MODE_OPTIONS: { mode: LensMode; label: string; tooltip: string }[] = [
  { mode: "stance", label: "STANCE", tooltip: "Colonial Stance + faction influence rings" },
  { mode: "heat", label: "HEAT", tooltip: "State attention / surveillance pressure" },
  { mode: "habitability", label: "HABITABILITY", tooltip: "Metabolic-rift biocapacity gradient" },
  { mode: "faction", label: "FACTION", tooltip: "Single-faction influence filter" },
  { mode: "collapse", label: "COLLAPSE", tooltip: "Collapse-moment contested territories" },
];

interface MapModeSelectorProps {
  factions?: FactionSummary[];
}

export function MapModeSelector({ factions = [] }: MapModeSelectorProps) {
  const lensMode = useMapStore((s) => s.lensMode);
  const setLensMode = useMapStore((s) => s.setLensMode);
  const factionFilter = useMapStore((s) => s.factionFilter);
  const setFactionFilter = useMapStore((s) => s.setFactionFilter);

  return (
    <div className="flex items-center gap-1">
      <div
        className="flex items-center gap-0.5 rounded-md border border-wet-concrete bg-void p-0.5"
        data-testid="map-mode-selector"
      >
        <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-ash">
          Lens
        </span>
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
      {lensMode === "faction" && factions.length > 0 && (
        <select
          data-testid="faction-filter-select"
          value={factionFilter ?? ""}
          onChange={(e) => setFactionFilter(e.target.value || null)}
          className="rounded-md border border-wet-concrete bg-void px-2 py-1 text-[11px] font-mono text-silver"
        >
          <option value="">Select faction…</option>
          {factions.map((f) => (
            <option key={f.id} value={f.id}>
              {f.id}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
