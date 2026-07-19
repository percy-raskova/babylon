/**
 * DoctrinePage — Track 3 / T3-5: "The Line" screen's first content.
 * Relocates the Doctrine Tree canvas (`DoctrineTakeover`, Epoch 3 Wave 6
 * Phase 0; Unit 7b's live Study affordance) off its old Zustand
 * `ui.takeover` overlay flag onto its own routed room (spec-117 §5c/§5, D2:
 * "each front gets a room of its own" — no god-dashboard). Canvas logic is
 * UNTOUCHED — only its mount point moved; `DoctrineTakeover.tsx` (still at
 * `components/takeovers/doctrine/`, kept in place for zero diff — the same
 * "relocate the mount point, not the file" precedent Track 2 T2-1 set for
 * `ScissorsChart`) and its live `/doctrine-tree/` data flow are exactly as
 * they were.
 *
 * Deliberately thin chrome, mirroring `CircuitPage`: a back-to-map link and
 * the live tick (read straight off `world.snapshot`, which keeps updating
 * here because the heartbeat/session lifecycle is owned by the `/game/:id`
 * layout route (`GameRoute`), not this leaf — switching screens never stops
 * the clock).
 */

import { useNavigate } from "react-router";
import { useStore } from "@/store";
import { DoctrineTakeover } from "@/components/takeovers/doctrine/DoctrineTakeover";

interface DoctrinePageProps {
  gameId: string;
}

export function DoctrinePage({ gameId }: DoctrinePageProps): React.JSX.Element {
  const navigate = useNavigate();
  const tick = useStore((s) => s.world.snapshot?.tick);

  return (
    <div
      data-testid="region-doctrine"
      className="flex h-screen w-screen flex-col overflow-hidden bg-void text-bone"
    >
      <header className="flex shrink-0 items-center justify-between border-b-2 border-ksbc-muted-1 bg-plate px-4 py-2">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate(`/game/${gameId}`)}
            data-testid="doctrine-back-to-map"
            className="font-mono text-[11px] uppercase tracking-widest text-accent-crimson hover:underline"
          >
            ← Map
          </button>
          <span className="font-mono text-sm font-semibold tracking-[4px] text-accent-crimson">
            THE LINE
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-[9px] uppercase tracking-widest text-ksbc-muted-2">Tick</span>
          <span
            className="font-mono text-xl font-bold text-spire"
            data-testid="doctrine-tick-value"
          >
            {tick ?? "no data"}
          </span>
        </div>
      </header>
      <div className="min-h-0 flex-1 p-4">
        <DoctrineTakeover gameId={gameId} />
      </div>
    </div>
  );
}
