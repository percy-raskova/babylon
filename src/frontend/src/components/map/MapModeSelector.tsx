/**
 * MapModeSelector — visible control for cycling the spec-070
 * political-topology map lens (stance/heat/habitability/faction/collapse).
 *
 * Adapted (spec-110 B2) to be a controlled component driven by the unified
 * `Lens` union (`@/lib/lens`) instead of reading/writing `mapStore`
 * directly — stores are B3 territory, so this component now takes the
 * active lens and a change callback as props. B3's store wrapper is
 * expected to be a thin `lens`/`setLens` pass-through.
 *
 * Distinct from `FramingSelector` (admin-level LOD, not ported in B2) and
 * the analytical `LensId` bar elsewhere in the v2 UI — see spec-093
 * Assumptions.
 *
 * When the "faction" lens is active, shows a faction picker dropdown
 * sourced from the balkanization block's faction list (FR-025).
 */

import { LENS_MODES, type Lens, type LensMode } from "@/lib/lens";
import type { FactionSummary } from "@/components/map/mapLensLayers";

const MODE_LABELS: Record<LensMode, { label: string; tooltip: string }> = {
  stance: { label: "STANCE", tooltip: "Colonial Stance + faction influence rings" },
  heat: { label: "HEAT", tooltip: "State attention / surveillance pressure" },
  habitability: { label: "HABITABILITY", tooltip: "Metabolic-rift biocapacity gradient" },
  faction: { label: "FACTION", tooltip: "Single-faction influence filter" },
  collapse: { label: "COLLAPSE", tooltip: "Collapse-moment contested territories" },
};

interface MapModeSelectorProps {
  /** The currently active lens. */
  lens: Lens;
  /** Called with the new lens when a mode button is clicked. */
  onLensChange?: (lens: Lens) => void;
  /** Currently selected faction for the "faction" lens mode. */
  factionFilter?: string | null;
  /** Called when a faction is chosen from the "faction" lens's picker. */
  onFactionFilterChange?: (factionId: string | null) => void;
  factions?: FactionSummary[];
}

export function MapModeSelector({
  lens,
  onLensChange,
  factionFilter = null,
  onFactionFilterChange,
  factions = [],
}: MapModeSelectorProps) {
  return (
    <div className="flex items-center gap-1">
      <div
        className="flex items-center gap-0.5 rounded-md border border-wet-steel bg-void p-0.5"
        data-testid="map-mode-selector"
      >
        <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-ash">
          Lens
        </span>
        {LENS_MODES.map((mode) => {
          const { label, tooltip } = MODE_LABELS[mode];
          const active = lens.kind === mode;
          return (
            <button
              key={mode}
              title={tooltip}
              data-testid={`lens-mode-${mode}`}
              aria-pressed={active}
              onClick={() => onLensChange?.({ kind: mode })}
              className={`rounded px-2 py-1 text-[11px] font-mono font-medium transition-colors ${
                active ? "bg-rupture text-void" : "text-fog hover:bg-concrete hover:text-rupture"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
      {lens.kind === "faction" && factions.length > 0 && (
        <select
          data-testid="faction-filter-select"
          value={factionFilter ?? ""}
          onChange={(e) => onFactionFilterChange?.(e.target.value || null)}
          className="rounded-md border border-wet-steel bg-void px-2 py-1 text-[11px] font-mono text-fog"
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
