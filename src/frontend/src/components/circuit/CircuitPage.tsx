/**
 * CircuitPage — Track 2 / T2-1: the Circuit screen's first content.
 * Relocates `ScissorsChart` (Program 23, ADR077-078) off its old
 * BottomDrawer tab onto its own routed room (spec-117 §5/§5b, D2: "each
 * front gets a room of its own" — no god-dashboard). Chart logic is
 * UNTOUCHED — only its mount point moved; `deriveCorrectionTicks` and the
 * live `/timeseries/` data flow are exactly as they were.
 *
 * T2-4/T2-6 (Slice A) add a left rail: the MELT gauge (a real instrument on
 * `latestMeltDrift`, reading `panels.timeseries` passively — the same data
 * `ScissorsChart` already drives) and the Fundamental Theorem meter (Wc vs
 * Vc, graph-wide + per-region — self-mounts `panels.economy`, the one new
 * fetch this screen needed). Neither touches `ScissorsChart` itself.
 * T2-7 (spec-117 §5b): the `wealth_by_class_role` composition — live,
 * already shipped on `panels.economy`, relocated here verbatim from
 * `EconomyDashboard.tsx` (its BottomDrawer copy is retired, not duplicated —
 * D2's "no god-dashboard" rule). Dollar-denominated wealth is Tier-0 content
 * (the money-form), so it renders unconditionally, same as before.
 *
 * T2-8/T2-9 — the Veil of Money (spec-117 §5d, D7): the two remaining
 * sections read `panels.economy.data.veil` (`web/game/veil.py`,
 * `EngineBridge.get_economy_dashboard`) and render either the real content
 * or a locked placeholder naming the doctrine node that unlocks it, linking
 * into the routed Doctrine page (`/game/:id/doctrine`). T3-5 retired the
 * doctrine takeover in favor of that route, so the study CTA is a plain
 * `navigate()` — no overlay flag involved.
 *
 * G4 (veil-leak closure, "Wave-2A compound leak"): the Fundamental
 * Theorem meter joins the exploitation/scissors sections as a THIRD
 * gated instrument — it reads `wage_flow_total`/`value_produced`/
 * `imperial_rent_gap`/`imperial_rent_gap_by_region` off the TOP-LEVEL
 * payload (not `veil.*`), which the server now gates identically
 * (`gate_value_axis_fields`); the audit found this rail rendering the
 * meter unconditionally, ungated by tier. `VeilLock` itself moved to
 * `components/shell/VeilLock.tsx` (shared with `EconomyDashboard.tsx`'s
 * own gated chips) rather than staying a CircuitPage-local component.
 *
 * Deliberately thin chrome: a back-to-map link and the live tick (read
 * straight off `world.snapshot`, which keeps updating here because the
 * heartbeat/session lifecycle is owned by the `/game/:id` layout route
 * (`GameRoute`), not this leaf — switching screens never stops the clock,
 * the whole point of the T2-0 routing pattern). The full TopBar/
 * TakeoverOverlay HUD stays map-only for now; a shared cross-screen header
 * is later Track 2/3 work, not this slice's scope.
 */

import { useEffect } from "react";
import { useNavigate } from "react-router";
import { useStore } from "@/store";
import { ScissorsChart } from "@/components/timeseries/ScissorsChart";
import { MeltGauge } from "@/components/timeseries/MeltGauge";
import { FundamentalTheoremMeter } from "@/components/circuit/FundamentalTheoremMeter";
import { StatChip } from "@/components/shell/StatChip";
import { SectionLabel } from "@/components/shell/SectionLabel";
import { VeilLock } from "@/components/shell/VeilLock";
import { BreakdownBar } from "@/components/inspect/BreakdownBar";
import { SOCIAL_ROLE_LABELS } from "@/components/map/mapLensLayers";
import type { EconomyDashboardPayload, VeilStatus } from "@/types/game";
import type { InspectionCompositionEntry } from "@/types/inspection";

interface CircuitPageProps {
  gameId: string;
}

/**
 * Wealth-by-role composition color (verbatim from `EconomyDashboard.tsx`,
 * T2-7 relocation) — see that file's history for the per-role rationale.
 */
const ROLE_CHIP_COLOR: Record<string, string> = {
  core_bourgeoisie: "text-rent",
  comprador_bourgeoisie: "text-heat",
  labor_aristocracy: "text-cadre",
  petty_bourgeoisie: "text-population",
  periphery_proletariat: "text-spire",
  internal_proletariat: "text-solidarity",
  lumpenproletariat: "text-thermal",
  carceral_enforcer: "text-laser",
};

function wealthCompositionEntries(
  wealthByRole: Record<string, number>,
): InspectionCompositionEntry[] {
  return Object.entries(wealthByRole).map(([role, value]) => ({
    key: SOCIAL_ROLE_LABELS[role] ?? role,
    value,
    color: ROLE_CHIP_COLOR[role],
  }));
}

/**
 * The Scissors section: the Tier-2 instrument itself (ScissorsChart) once
 * unlocked, its veiled placeholder below Tier 2, or nothing while
 * `panels.economy` has not yet loaded (an honest loading gap — never a
 * flash of the real chart before the tier is known).
 */
function renderScissorsSection(
  veil: VeilStatus | undefined,
  gameId: string,
  onStudy: () => void,
): React.JSX.Element | null {
  if (veil === undefined) {
    return null;
  }
  if (veil.tier >= 2) {
    return <ScissorsChart gameId={gameId} />;
  }
  return (
    <VeilLock label={veil.next_unlock_label ?? "Theory"} onStudy={onStudy} section="scissors" />
  );
}

/**
 * The Fundamental Theorem instrument: the real meter once Tier 1 unlocks
 * the wage-vs-value-produced axis, its veiled placeholder below Tier 1, or
 * nothing while `panels.economy` has not yet loaded (G4, "Wave-2A compound
 * leak" — this rail used to render the meter unconditionally, reading the
 * now-gated top-level `wage_flow_total`/`value_produced`/`imperial_rent_
 * gap`/`imperial_rent_gap_by_region` fields regardless of tier).
 */
function renderFundamentalTheoremSection(
  economyData: EconomyDashboardPayload | null,
  gameId: string,
  onStudy: () => void,
): React.JSX.Element | null {
  const veil = economyData?.veil;
  if (veil === undefined) {
    return null;
  }
  if (veil.tier >= 1) {
    return <FundamentalTheoremMeter gameId={gameId} />;
  }
  return (
    <VeilLock
      label={veil.next_unlock_label ?? "Theory"}
      onStudy={onStudy}
      section="fundamental-theorem"
    />
  );
}

export function CircuitPage({ gameId }: CircuitPageProps): React.JSX.Element {
  const navigate = useNavigate();
  const tick = useStore((s) => s.world.snapshot?.tick);
  const timeseries = useStore((s) => s.panels.timeseries.data);
  const economyData = useStore((s) => s.panels.economy.data);
  const fetchEconomy = useStore((s) => s.panels.economy.fetch);
  const setEconomyMounted = useStore((s) => s.panels.economy.setMounted);

  useEffect(() => {
    setEconomyMounted(true);
    void fetchEconomy(gameId);
    return () => setEconomyMounted(false);
  }, [gameId, fetchEconomy, setEconomyMounted]);

  const studyDoctrine = (): void => {
    // The Doctrine surface is its own route since T3-5 (the takeover was
    // retired) — a plain navigation, no overlay flag involved.
    navigate(`/game/${gameId}/doctrine`);
  };

  const veil: VeilStatus | undefined = economyData?.veil;

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
      <div className="flex min-h-0 flex-1 gap-4 p-4">
        <aside
          className="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto"
          data-testid="circuit-instruments"
        >
          <div className="border-2 border-ksbc-muted-1 bg-plate">
            <MeltGauge payload={timeseries} />
          </div>
          <div className="border-2 border-ksbc-muted-1 bg-plate">
            {renderFundamentalTheoremSection(economyData, gameId, studyDoctrine)}
          </div>
        </aside>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto">
          {economyData && (
            <div>
              <SectionLabel>Wealth by Class</SectionLabel>
              <BreakdownBar entries={wealthCompositionEntries(economyData.wealth_by_class_role)} />
            </div>
          )}

          {veil && (
            <div>
              <SectionLabel>Exploitation</SectionLabel>
              {veil.tier >= 1 ? (
                <div className="flex flex-wrap gap-1.5" data-testid="circuit-exploitation-chips">
                  <StatChip
                    label="Value Produced"
                    value={veil.value_produced}
                    format={(v) => v.toFixed(1)}
                  />
                  <StatChip
                    label="Exploitation Rate"
                    value={veil.exploitation_rate}
                    format={(v) => v.toFixed(3)}
                    metric="exploitation_rate"
                  />
                </div>
              ) : (
                <VeilLock
                  label={veil.next_unlock_label ?? "Theory"}
                  onStudy={studyDoctrine}
                  section="exploitation"
                />
              )}
            </div>
          )}

          <div className="min-h-0 flex-1">
            <SectionLabel>The Scissors</SectionLabel>
            {renderScissorsSection(veil, gameId, studyDoctrine)}
          </div>
        </div>
      </div>
    </div>
  );
}
