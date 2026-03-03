/**
 * Top bar with tick counter, persistent indicators, user menu, and resolve button.
 */

import { PersistentIndicators } from "@/components/charts/PersistentIndicators";
import type { GameSnapshot } from "@/types/game";

interface TopBarProps {
  snapshot: GameSnapshot | null;
  gameId: string;
  username: string;
  resolving: boolean;
  onResolve: () => void;
  onBack: () => void;
  onLogout: () => void;
}

export function TopBar({
  snapshot,
  gameId,
  username,
  resolving,
  onResolve,
  onBack,
  onLogout,
}: TopBarProps) {
  return (
    <div className="flex shrink-0 items-center justify-between border-b border-soot bg-void px-4 py-2">
      {/* Left: back + game ID */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="rounded-md border border-wet-concrete px-3 py-1.5 text-xs text-silver hover:border-silver"
        >
          &larr; Games
        </button>
        <span className="font-mono text-xs text-ash">{gameId.slice(0, 8)}...</span>
      </div>

      {/* Center: tick + indicators */}
      <div className="flex items-center gap-6">
        {snapshot && (
          <div className="flex items-baseline gap-2">
            <span className="text-[11px] uppercase tracking-wider text-ash">Tick</span>
            <span className="font-mono text-2xl font-bold text-gold">{snapshot.tick}</span>
          </div>
        )}
        {snapshot && <PersistentIndicators snapshot={snapshot} />}
      </div>

      {/* Right: resolve + user */}
      <div className="flex items-center gap-3">
        <button
          onClick={onResolve}
          disabled={resolving}
          className="rounded-md bg-gold px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-void hover:brightness-110 disabled:opacity-50"
        >
          {resolving ? "Resolving..." : "Resolve Tick"}
        </button>
        <span className="text-sm text-silver">{username}</span>
        <button
          onClick={onLogout}
          className="rounded-md border border-wet-concrete px-3 py-1.5 text-xs text-silver hover:border-silver"
        >
          Logout
        </button>
      </div>
    </div>
  );
}
