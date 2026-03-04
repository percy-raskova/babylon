/**
 * LensBar — horizontal lens selector for switching analytical perspectives.
 *
 * Four lenses (Economic, Political, Social, Strategic) rendered as
 * compact buttons with icons. Active lens highlighted in GOLD.
 */

import { BarChart3, Vote, Users, Target } from "lucide-react";
import { useLens } from "@/hooks/useLens";
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
    </div>
  );
}
