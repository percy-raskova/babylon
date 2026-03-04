/**
 * Top bar — tick counter, urgency-colored indicators, user menu, resolve button.
 *
 * Background tint shifts based on the highest-severity indicator:
 * normal = none, warning = faint amber, critical = faint crimson.
 * Includes indicator selection popover for customization.
 */

import { useMemo, useState, useRef, useEffect } from "react";
import { Settings } from "lucide-react";
import { PersistentIndicators } from "@/components/charts/PersistentIndicators";
import { useUIStore } from "@/stores/uiStore";
import { getIndicatorById, getIndicatorUrgency, INDICATOR_LIST } from "@/lib/lensDefinitions";
import type { GameSnapshot, IndicatorId } from "@/types/game";

interface TopBarProps {
  snapshot: GameSnapshot | null;
  gameId: string;
  username: string;
  resolving: boolean;
  onResolve: () => void;
  onBack: () => void;
  onLogout: () => void;
}

const URGENCY_TINTS: Record<string, string> = {
  normal: "",
  warning: "bg-warning-amber/5",
  critical: "bg-crimson/8",
};

export function TopBar({
  snapshot,
  gameId,
  username,
  resolving,
  onResolve,
  onBack,
  onLogout,
}: TopBarProps) {
  const pinnedIndicators = useUIStore((s) => s.pinnedIndicators);
  const unreadCount = useUIStore((s) => s.unreadCount);
  const [showPopover, setShowPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close popover on outside click
  useEffect(() => {
    if (!showPopover) return;
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowPopover(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showPopover]);

  const highestUrgency = useMemo(() => {
    if (!snapshot) return "normal";
    let worst: "normal" | "warning" | "critical" = "normal";
    for (const id of pinnedIndicators) {
      const def = getIndicatorById(id);
      const val = def.compute(snapshot);
      const urgency = getIndicatorUrgency(val, def.thresholds);
      if (urgency === "critical") return "critical";
      if (urgency === "warning") worst = "warning";
    }
    return worst;
  }, [snapshot, pinnedIndicators]);

  const tintClass = URGENCY_TINTS[highestUrgency];

  return (
    <div
      className={`flex shrink-0 items-center justify-between border-b border-soot bg-void px-4 py-2 transition-colors duration-500 ${tintClass}`}
    >
      {/* Left: back + game ID */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="rounded-md border border-wet-concrete px-3 py-1.5 text-xs text-silver transition-colors hover:border-silver hover:text-bone"
        >
          &larr; Games
        </button>
        <span className="font-mono text-xs text-ash">{gameId.slice(0, 8)}...</span>
      </div>

      {/* Center: tick + indicators + settings */}
      <div className="flex items-center gap-4">
        {snapshot && (
          <div className="flex items-baseline gap-2">
            <span className="text-[11px] uppercase tracking-wider text-ash">Tick</span>
            <span className="font-mono text-2xl font-bold text-gold">{snapshot.tick}</span>
          </div>
        )}
        {snapshot && <PersistentIndicators snapshot={snapshot} />}

        {/* Indicator settings popover */}
        <div className="relative" ref={popoverRef}>
          <button
            onClick={() => setShowPopover(!showPopover)}
            className="flex h-6 w-6 items-center justify-center rounded text-ash transition-colors hover:text-silver"
            title="Configure indicators"
          >
            <Settings size={14} />
          </button>
          {showPopover && (
            <IndicatorPopover pinnedIds={pinnedIndicators} onClose={() => setShowPopover(false)} />
          )}
        </div>

        {unreadCount > 0 && (
          <span
            className="flex h-5 min-w-5 items-center justify-center rounded-full bg-crimson px-1.5 text-[10px] font-bold text-bone"
            title={`${unreadCount} unread events`}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </div>

      {/* Right: resolve + user */}
      <div className="flex items-center gap-3">
        <button
          onClick={onResolve}
          disabled={resolving}
          className="rounded-md bg-gold px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-void transition-all hover:brightness-110 disabled:opacity-50"
        >
          {resolving ? "Resolving..." : "Resolve Tick"}
        </button>
        <span className="text-sm text-silver">{username}</span>
        <button
          onClick={onLogout}
          className="rounded-md border border-wet-concrete px-3 py-1.5 text-xs text-silver transition-colors hover:border-silver hover:text-bone"
        >
          Logout
        </button>
      </div>
    </div>
  );
}

/** Popover for selecting which indicators to pin in the top bar. */
function IndicatorPopover({
  pinnedIds,
  onClose,
}: {
  pinnedIds: IndicatorId[];
  onClose: () => void;
}) {
  const setPinnedIndicators = useUIStore((s) => s.setPinnedIndicators);
  const resetPreferences = useUIStore((s) => s.resetPreferences);
  const pinnedSet = new Set(pinnedIds);

  const toggleIndicator = (id: IndicatorId) => {
    if (pinnedSet.has(id)) {
      // Don't allow fewer than 1 indicator
      if (pinnedIds.length > 1) {
        setPinnedIndicators(pinnedIds.filter((i) => i !== id));
      }
    } else {
      // Cap at 6 indicators
      if (pinnedIds.length < 6) {
        setPinnedIndicators([...pinnedIds, id]);
      }
    }
  };

  return (
    <div className="absolute right-0 top-8 z-50 w-56 rounded-lg border border-wet-concrete bg-dark-metal p-2 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-widest text-gold">
          Indicators
        </span>
        <span className="text-[9px] text-ash">{pinnedIds.length}/6</span>
      </div>

      <div className="flex max-h-48 flex-col gap-0.5 overflow-auto">
        {INDICATOR_LIST.map((def) => {
          const checked = pinnedSet.has(def.id);
          return (
            <label
              key={def.id}
              className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-[11px] transition-colors hover:bg-soot"
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggleIndicator(def.id)}
                className="h-3 w-3 accent-gold"
              />
              <span className={checked ? "text-bone" : "text-ash"}>{def.label}</span>
            </label>
          );
        })}
      </div>

      <div className="mt-2 flex gap-2 border-t border-soot pt-2">
        <button
          onClick={() => {
            resetPreferences();
            onClose();
          }}
          className="flex-1 rounded border border-wet-concrete px-2 py-1 text-[10px] text-ash transition-colors hover:text-silver"
        >
          Reset Defaults
        </button>
        <button
          onClick={onClose}
          className="flex-1 rounded bg-gold/10 px-2 py-1 text-[10px] text-gold transition-colors hover:bg-gold/20"
        >
          Done
        </button>
      </div>
    </div>
  );
}
