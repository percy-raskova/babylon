/**
 * CircuitPage — Track 2 / T2-1: the Circuit screen's first content.
 * Relocates `ScissorsChart` (Program 23, ADR077-078) off its old
 * BottomDrawer tab onto its own routed room (spec-117 §5/§5b, D2: "each
 * front gets a room of its own" — no god-dashboard). Chart logic is
 * UNTOUCHED — only its mount point moved; `deriveCorrectionTicks` and the
 * live `/timeseries/` data flow are exactly as they were.
 *
 * Deliberately thin chrome: a back-to-map link and the live tick (read
 * straight off `world.snapshot`, which keeps updating here because the
 * heartbeat/session lifecycle is owned by the `/game/:id` layout route
 * (`GameRoute`), not this leaf — switching screens never stops the clock,
 * the whole point of the T2-0 routing pattern). The full TopBar/
 * TakeoverOverlay HUD stays map-only for now; a shared cross-screen header
 * is later Track 2/3 work, not this slice's scope.
 */

import { useNavigate } from "react-router";
import { useStore } from "@/store";
import { ScissorsChart } from "@/components/timeseries/ScissorsChart";

interface CircuitPageProps {
  gameId: string;
}

export function CircuitPage({ gameId }: CircuitPageProps): React.JSX.Element {
  const navigate = useNavigate();
  const tick = useStore((s) => s.world.snapshot?.tick);

  return (
    <div
      data-testid="region-circuit"
      className="flex h-screen w-screen flex-col overflow-hidden bg-void text-bone"
    >
      <header className="flex shrink-0 items-center justify-between border-b-2 border-ksbc-muted-1 bg-plate px-4 py-2">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate(`/game/${gameId}`)}
            data-testid="circuit-back-to-map"
            className="font-mono text-[11px] uppercase tracking-widest text-accent-crimson hover:underline"
          >
            ← Map
          </button>
          <span className="font-mono text-sm font-semibold tracking-[4px] text-accent-crimson">
            THE CIRCUIT
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-[9px] uppercase tracking-widest text-ksbc-muted-2">Tick</span>
          <span className="font-mono text-xl font-bold text-spire" data-testid="circuit-tick-value">
            {tick ?? "no data"}
          </span>
        </div>
      </header>
      <div className="min-h-0 flex-1 p-4">
        <ScissorsChart gameId={gameId} />
      </div>
    </div>
  );
}
