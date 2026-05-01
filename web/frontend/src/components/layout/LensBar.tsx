/**
 * LensBar — horizontal lens selector for switching analytical perspectives.
 *
 * Four lenses (Economic, Political, Social, Strategic) rendered as
 * compact buttons with icons. Active lens highlighted in GOLD.
 */

import { BarChart3, Vote, Users, Target } from "lucide-react";
import { useLens } from "@/hooks/useLens";
import { useMapStore } from "@/stores/mapStore";
import { LENS_LIST } from "@/lib/lensDefinitions";
import type { LensId } from "@/types/game";

const LENS_ICONS: Record<LensId, React.ComponentType<{ size?: number }>> = {
  economic: BarChart3,
  political: Vote,
  social: Users,
  strategic: Target,
};

export function LensBar() {
  const { activeLens, switchLens } = useLens();
  const layerOpacity = useMapStore((s) => s.layerOpacity);
  const setLayerOpacity = useMapStore((s) => s.setLayerOpacity);
  const showEdges = useMapStore((s) => s.showEdges);
  const toggleEdges = useMapStore((s) => s.toggleEdges);

  return (
    <div className="flex shrink-0 items-center gap-1 border-t border-soot bg-void/80 px-3 py-1">
      <span className="mr-2 text-[9px] uppercase tracking-widest text-ash">Lens</span>
      {LENS_LIST.map((lens) => {
        const Icon = LENS_ICONS[lens.id];
        const isActive = activeLens === lens.id;
        return (
          <button
            key={lens.id}
            onClick={() => switchLens(lens.id)}
            title={lens.description}
            className={`flex items-center gap-1.5 rounded px-3 py-1 text-[11px] font-medium transition-colors ${
              isActive ? "bg-gold/10 text-gold" : "text-ash hover:bg-soot hover:text-silver"
            }`}
          >
            <Icon size={13} />
            {lens.name}
          </button>
        );
      })}

      {/* Divider */}
      <div className="mx-2 h-4 w-px bg-wet-concrete" />

      {/* Opacity slider (migrated from LayerControls) */}
      <label className="flex items-center gap-1.5 text-[10px] text-ash">
        Opacity
        <input
          type="range"
          min={0}
          max={100}
          value={Math.round(layerOpacity * 100)}
          onChange={(e) => setLayerOpacity(Number(e.target.value) / 100)}
          className="h-1 w-16 appearance-none rounded bg-wet-concrete [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-gold"
        />
      </label>

      {/* Edge toggle (migrated from LayerControls) */}
      <button
        onClick={toggleEdges}
        className={`rounded px-2 py-0.5 text-[11px] ${
          showEdges ? "bg-dark-metal text-data-green" : "text-ash hover:text-silver"
        }`}
      >
        Edges
      </button>
    </div>
  );
}
