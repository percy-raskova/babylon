/**
 * Trap deviation indicator.
 *
 * Shows strategic warnings when the player drifts into one of three
 * ideological traps: Liberal, Ultra-Left, or Rightist.
 * Displayed as a dismissible alert bar above the game view.
 */

import { useState } from "react";
import type { TrapDetectionResult } from "@/types/game";

interface TrapIndicatorProps {
  traps: TrapDetectionResult | undefined;
}

/** Human-readable trap descriptions for the player. */
const TRAP_DESCRIPTIONS: Record<string, { name: string; warning: string; severe: string }> = {
  liberal: {
    name: "Liberal Deviation",
    warning:
      "Your organization is drifting toward reformism. You're spending money and building coalitions, but not developing cadre or raising consciousness. Consider more education and mobilization.",
    severe:
      "LIBERAL TRAP: Your organization has been co-opted by the Democratic Party machine. Your 'pragmatic' approach has produced an NGO, not a revolutionary organization. Game Over.",
  },
  ultra_left: {
    name: "Ultra-Left Deviation",
    warning:
      "Your organization is substituting itself for the masses. Too many attacks without a mass base will bring state repression you can't withstand. Build sympathizer networks before escalating.",
    severe:
      "ULTRA-LEFT TRAP: Your adventurist tactics have isolated you from the working class and brought the full weight of state repression. Your organization has been destroyed. Game Over.",
  },
  rightist: {
    name: "Rightist Deviation",
    warning:
      "Your organization is avoiding necessary confrontation. Aid work and study circles are important but insufficient. Fascism is rising and you're not challenging it. Mobilize!",
    severe:
      "RIGHTIST TRAP: While you focused on service provision and education, fascist forces consolidated power. Your organization is now irrelevant. Game Over.",
  },
};

/** Derive severity-based style tokens for the trap alert. */
function getTrapStyles(
  isSevere: boolean,
  isModerate: boolean,
): { bgColor: string; textColor: string } {
  if (isSevere) {
    return {
      bgColor: "bg-[#3a0a0a] border-[#ff4040]",
      textColor: "text-[#ff6060]",
    };
  }
  if (isModerate) {
    return {
      bgColor: "bg-[#2a1a0a] border-[#c8a860]",
      textColor: "text-[#c8a860]",
    };
  }
  return {
    bgColor: "bg-[#1a1a30] border-[#4a7cff]",
    textColor: "text-[#8ab4ff]",
  };
}

export function TrapIndicator({ traps }: TrapIndicatorProps) {
  const [dismissed, setDismissed] = useState<string | null>(null);

  if (!traps || !traps.active_trap) return null;

  const activeTrapKey = traps.active_trap as "liberal" | "ultra_left" | "rightist";
  const activeTrap = traps[activeTrapKey];
  if (!activeTrap || activeTrap.severity === "none") return null;

  if (dismissed === activeTrap.trap_type && activeTrap.severity === "mild") {
    return null;
  }

  const desc = TRAP_DESCRIPTIONS[activeTrap.trap_type];
  if (!desc) return null;

  const isSevere = activeTrap.severity === "severe";
  const isModerate = activeTrap.severity === "moderate";
  const { bgColor, textColor } = getTrapStyles(isSevere, isModerate);

  return (
    <div className={`mb-3 shrink-0 rounded-lg border p-3 ${bgColor}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className={`mb-1 text-sm font-bold uppercase tracking-wider ${textColor}`}>
            ⚠ {desc.name} ({activeTrap.severity})
          </div>
          <p className="text-[13px] leading-relaxed text-bone">
            {isSevere ? desc.severe : desc.warning}
          </p>
          {activeTrap.indicators.length > 0 && !isSevere && (
            <ul className="mt-2 space-y-0.5 text-xs text-ash">
              {activeTrap.indicators.map((ind, i) => (
                <li key={i}>• {ind}</li>
              ))}
            </ul>
          )}
        </div>
        {!isSevere && (
          <button
            onClick={() => setDismissed(activeTrap.trap_type)}
            className="shrink-0 rounded border border-wet-concrete px-2 py-1 text-xs text-ash hover:border-silver hover:text-silver"
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}
