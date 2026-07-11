/**
 * FramingSelector — toolbar for switching between admin framing levels
 * (spec-112 C5; reordered spec-113 Lane B, DESIGN_BIBLE.md §9.2/§2.2).
 * Renders as a compact button group, visually matching `MapLensBar`'s chip
 * idiom — the two mount side by side in `MapControls`' cluster ("Scale" vs.
 * "Lens").
 *
 * Bible §9.2 amendment 2 (the Carto addendum's cartography inversion):
 * county/state are the PRIMARY framings now (real political cartography is
 * the default look, §7), hex is demoted to a deep-zoom entry — this is a
 * pure `FRAMING_OPTIONS` reorder (county first, hex last), no behavior
 * change: `framing`/`onFramingChange` stay a controlled pass-through, and
 * `mapSlice.framing`'s own default is Lane C's concern (see the module's
 * lane-ownership note in `DeckGLMap.tsx`) — this component works correctly
 * with whatever default lands there.
 *
 * Controlled component (props: framing, onFramingChange — the cockpit B2
 * convention `MapModeSelector` established, ported forward to `MapLensBar`):
 * no store reads. `MapStage`/`DeckGLMap` wire it to `mapSlice.framing`/
 * `setFraming`.
 *
 * Ported from the OLD app's `FramingSelector`
 * (web/frontend/src/components/map/FramingSelector.tsx), which read/wrote
 * `mapStore` directly — stores are B3 territory here.
 */

import type { AdminLevel } from "@/types/game";

const FRAMING_OPTIONS: { level: AdminLevel; label: string; tooltip: string }[] = [
  { level: "county", label: "CTY", tooltip: "County (FIPS) — the default political read" },
  { level: "state", label: "ST", tooltip: "State — colonial-baseline dissolve" },
  { level: "cz", label: "CZ", tooltip: "Commuting Zone" },
  { level: "msa", label: "MSA", tooltip: "Metropolitan Statistical Area" },
  { level: "bea_ea", label: "EA", tooltip: "BEA Economic Area" },
  {
    level: "hex",
    label: "HEX",
    tooltip: "H3 Hexagon — deep-zoom tactical register, not the default look",
  },
];

interface FramingSelectorProps {
  /** The currently active admin framing level. */
  framing: AdminLevel;
  /** Called with the new level when a framing button is clicked. */
  onFramingChange?: (level: AdminLevel) => void;
}

export function FramingSelector({ framing, onFramingChange }: FramingSelectorProps) {
  return (
    <div
      className="flex items-center gap-0.5 rounded-md border border-wet-steel bg-void p-0.5"
      data-testid="framing-selector"
    >
      <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-ash">
        Scale
      </span>
      {FRAMING_OPTIONS.map(({ level, label, tooltip }) => {
        const active = framing === level;
        return (
          <button
            key={level}
            title={tooltip}
            data-testid={`framing-${level}`}
            aria-pressed={active}
            onClick={() => onFramingChange?.(level)}
            className={`rounded px-2 py-1 text-[11px] font-mono font-medium transition-colors ${
              active ? "bg-rupture text-void" : "text-fog hover:bg-concrete hover:text-rupture"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
