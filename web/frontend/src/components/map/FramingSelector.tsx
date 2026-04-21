/**
 * FramingSelector — toolbar for switching between admin framing levels.
 *
 * Renders as a compact button group in the map area, visually similar
 * to a GIS basemap switch.  Each button represents an administrative
 * aggregation level (state / county / CZ / BEA EA / MSA / hex).
 */

import { useMapStore } from "@/stores/mapStore";
import { useGameStore } from "@/stores/gameStore";
import type { AdminLevel } from "@/types/game";

const FRAMING_OPTIONS: { level: AdminLevel; label: string; tooltip: string }[] = [
  { level: "state", label: "ST", tooltip: "State — Michigan" },
  { level: "bea_ea", label: "EA", tooltip: "BEA Economic Area" },
  { level: "msa", label: "MSA", tooltip: "Metropolitan Statistical Area" },
  { level: "cz", label: "CZ", tooltip: "Commuting Zone" },
  { level: "county", label: "CTY", tooltip: "County (FIPS)" },
  { level: "hex", label: "HEX", tooltip: "H3 Hexagon (raw)" },
];

export function FramingSelector() {
  const activeFraming = useMapStore((s) => s.activeFraming);
  const setActiveFraming = useMapStore((s) => s.setActiveFraming);
  const sessionId = useGameStore((s) => s.sessionId);
  const fetchMapData = useGameStore((s) => s.fetchMapData);

  const handleSelect = (level: AdminLevel) => {
    setActiveFraming(level);
    if (sessionId) {
      void fetchMapData(sessionId, level);
    }
  };

  return (
    <div className="flex items-center gap-0.5 rounded-md border border-wet-concrete bg-void p-0.5">
      <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-ash">
        Scale
      </span>
      {FRAMING_OPTIONS.map(({ level, label, tooltip }) => (
        <button
          key={level}
          title={tooltip}
          data-testid={`framing-${level}`}
          onClick={() => handleSelect(level)}
          className={`rounded px-2 py-1 text-[11px] font-mono font-medium transition-colors ${
            activeFraming === level
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
