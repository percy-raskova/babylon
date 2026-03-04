/**
 * Endgame notification overlay — displays when a terminal condition is reached.
 */

import type { EndgameData } from "@/types/game";

/** Human-readable labels for endgame outcomes. */
const ENDGAME_LABELS: Record<string, { title: string; color: string }> = {
  REVOLUTIONARY_VICTORY: { title: "Revolutionary Victory", color: "text-crimson" },
  ECOLOGICAL_COLLAPSE: { title: "Ecological Collapse", color: "text-gold" },
  FASCIST_CONSOLIDATION: { title: "Fascist Consolidation", color: "text-ash" },
};

interface EndgameOverlayProps {
  endgame: EndgameData;
  onDismiss: () => void;
  onBack: () => void;
}

export function EndgameOverlay({ endgame, onDismiss, onBack }: EndgameOverlayProps) {
  const label = ENDGAME_LABELS[endgame.outcome];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="mx-4 max-w-lg rounded-xl border border-wet-concrete bg-dark-metal p-8 text-center shadow-2xl">
        <h2
          className={`mb-2 text-3xl font-bold uppercase tracking-wider ${label?.color ?? "text-gold"}`}
        >
          {label?.title ?? endgame.outcome}
        </h2>
        <p className="mb-1 text-sm text-ash">Tick {endgame.tick}</p>
        {endgame.summary && <p className="mb-6 text-sm text-silver">{endgame.summary}</p>}
        <button
          onClick={onDismiss}
          className="rounded-md border border-wet-concrete px-6 py-2 text-sm text-silver hover:border-silver"
        >
          Continue Viewing
        </button>
        <button
          onClick={onBack}
          className="ml-3 rounded-md bg-gold px-6 py-2 text-sm font-semibold text-void hover:brightness-110"
        >
          Back to Games
        </button>
      </div>
    </div>
  );
}
