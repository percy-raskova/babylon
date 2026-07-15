/**
 * TopBar — Layer 1 chrome, the floating full-width strip (architecture
 * §1.1/§1.2's `StatusBar` → `TopBar` migrate row). Real `/summary/` fields
 * (tick, profit rate, imperial rent Φ, population, alert counts), the
 * takeover-open buttons (Wire / Dialectic / Chronicle / Network), and `SpeedControls`
 * (bible §5.1's identity/date/speed cluster). An instance of `FloatingPanel`
 * (anchor="top") per architecture §1.3 — no `title`/`onToggle` given, so
 * `FloatingPanel` renders no header and TopBar's own layout owns the whole
 * strip.
 *
 * Four Installer clusters (bible §5.1, §9b), border-divided:
 * [identity/tick] [Φ/Profit probes + alerts] [takeovers] [SpeedControls].
 * The Profit and Rent Φ chips carry real `web/game/provenance.py`
 * `METRIC_PROVENANCE` keys (`profit_rate`, `imperial_rent`) so they're
 * clickable probes per DESIGN_BIBLE §4's "every StatChip in the TopBar is
 * itself a Probe"; Pop stays a plain (non-clickable) chip — there is no
 * `population_total`/`population` entry in the manifest, and a dead
 * click affordance would be dishonest (Constitution III.11).
 *
 * Keeps `region-statusbar`/`tick-value` testids (frozen — real-loop.spec.ts,
 * end-turn-flow.spec.ts, briefing-map-smoke.spec.ts, map-lens-cycling.spec.ts
 * all read them).
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { SpeedControls } from "./SpeedControls";
import { keyButtonClass } from "./installerKit";
import { StatChip } from "@/components/shell/StatChip";
import type { TakeoverKind } from "@/store";

interface TopBarProps {
  gameId: string;
}

export function TopBar({ gameId }: TopBarProps): React.JSX.Element {
  const tick = useStore((s) => s.world.snapshot?.tick);
  const summaryData = useStore((s) => s.panels.summary.data);
  const fetchSummary = useStore((s) => s.panels.summary.fetch);
  const setSummaryMounted = useStore((s) => s.panels.summary.setMounted);
  const openTakeover = useStore((s) => s.ui.openTakeover);

  useEffect(() => {
    setSummaryMounted(true);
    void fetchSummary(gameId);
    return () => setSummaryMounted(false);
  }, [gameId, fetchSummary, setSummaryMounted]);

  const eventCounts = summaryData?.event_counts;
  const hasAlerts = eventCounts !== undefined && eventCounts.critical + eventCounts.warning > 0;

  return (
    <FloatingPanel anchor="top" testId="region-statusbar">
      <div className="flex items-center justify-between px-4 py-2" aria-label="StatusBar">
        {/* Cluster 1 — identity/tick */}
        <div className="flex items-center gap-4">
          <span className="font-mono text-sm font-semibold tracking-[4px] text-accent-crimson">
            BABYLON COCKPIT
          </span>
          <div className="flex items-baseline gap-2 border-l-2 border-ksbc-muted-1 pl-4">
            <span className="text-[9px] uppercase tracking-widest text-ksbc-muted-2">Tick</span>
            <span
              className="bloom-spire font-mono text-xl font-bold text-spire"
              data-testid="tick-value"
            >
              {tick ?? "no data"}
            </span>
          </div>
        </div>

        {/* Cluster 2 — Φ/Profit probes + alerts */}
        <div className="flex items-center gap-2">
          <StatChip
            label="Profit"
            value={summaryData?.profit_rate ?? null}
            format={(v) => v.toFixed(3)}
            colorClassName="text-rupture"
            metric="profit_rate"
          />
          <StatChip
            label="Rent Φ"
            value={summaryData?.imperial_rent ?? null}
            format={(v) => v.toFixed(2)}
            colorClassName="text-rent"
            metric="imperial_rent"
          />
          <StatChip
            label="Pop"
            value={summaryData?.population_total ?? null}
            format={(v) => v.toLocaleString()}
            colorClassName="text-population"
          />
          {hasAlerts && (
            <div className="flex items-center gap-1" data-testid="alert-counts">
              {eventCounts.critical > 0 && (
                <span
                  title={`${eventCounts.critical} critical events`}
                  className="alert-throb-frame border-2 border-accent-crimson bg-accent-crimson px-1.5 py-0.5 font-mono text-[10px] font-bold text-ink"
                >
                  {eventCounts.critical}
                </span>
              )}
              {eventCounts.warning > 0 && (
                <span
                  title={`${eventCounts.warning} warning events`}
                  className="border-2 border-heat bg-heat px-1.5 py-0.5 font-mono text-[10px] font-bold text-void"
                >
                  {eventCounts.warning}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Cluster 3 — takeovers */}
        <div
          className="flex items-center gap-1 border-l-2 border-ksbc-muted-1 pl-3"
          role="group"
          aria-label="Takeovers"
        >
          <TakeoverButton kind="wire" label="Wire" onOpen={openTakeover} />
          <TakeoverButton kind="dialectic" label="Dialectic" onOpen={openTakeover} />
          <TakeoverButton kind="chronicle" label="Chronicle" onOpen={openTakeover} />
          <TakeoverButton kind="network" label="Network" onOpen={openTakeover} />
        </div>

        {/* Cluster 4 — speed */}
        <SpeedControls gameId={gameId} />
      </div>
    </FloatingPanel>
  );
}

function TakeoverButton({
  kind,
  label,
  onOpen,
}: {
  kind: TakeoverKind;
  label: string;
  onOpen: (kind: TakeoverKind) => void;
}): React.JSX.Element {
  return (
    <button
      onClick={() => onOpen(kind)}
      data-testid={`open-${kind}`}
      className={keyButtonClass(false, "px-2 py-1 text-[9px]")}
    >
      {label}
    </button>
  );
}
