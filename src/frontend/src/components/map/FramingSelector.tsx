/**
 * FramingSelector — toolbar for switching between admin framing levels
 * (spec-112 C5). Renders as a compact button group, visually matching
 * `MapModeSelector`'s chip idiom — the two mount side by side in the map
 * controls stack ("Scale" vs. "Lens").
 *
 * Controlled component (props: framing, onFramingChange — the cockpit B2
 * convention `MapModeSelector` established): no store reads. `MapPanel`
 * wires it to `mapSlice.framing`/`setFraming`.
 *
 * Ported from the OLD app's `FramingSelector`
 * (web/frontend/src/components/map/FramingSelector.tsx), which read/wrote
 * `mapStore` directly — stores are B3 territory here.
 */

import type { AdminLevel } from "@/types/game";

const FRAMING_OPTIONS: { level: AdminLevel; label: string; tooltip: string }[] = [
  { level: "state", label: "ST", tooltip: "State — Michigan" },
  { level: "bea_ea", label: "EA", tooltip: "BEA Economic Area" },
  { level: "msa", label: "MSA", tooltip: "Metropolitan Statistical Area" },
  { level: "cz", label: "CZ", tooltip: "Commuting Zone" },
  { level: "county", label: "CTY", tooltip: "County (FIPS)" },
  { level: "hex", label: "HEX", tooltip: "H3 Hexagon (raw)" },
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
