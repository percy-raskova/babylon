/**
 * EconomyDashboard — the `/economy/` left-drawer panel (Wave 2 W2.2a,
 * `reports/wave2-implementation-map.md`). Stat chips over the graph-wide
 * `EconomyDashboardPayload`, the `wealth_by_class_role` composition, the
 * wealth trajectory (reusing `panels.timeseries`'s real `wealth` array —
 * no second fetch), and a crisis-phase-transition timeline read straight
 * from the journal.
 *
 * `panels.economy.setMounted` had zero production call sites before this
 * component (Wave 2 recon: the panel was fully plumbed but never fetched)
 * — this mount effect is what closes that loop, following the exact
 * `TimeseriesChart`/`Outliner` mount idiom (`setMounted(true)` + `fetch` on
 * mount, `setMounted(false)` on unmount).
 *
 * Lives in `BottomDrawer`'s "economy" tab, always mounted (visibility
 * toggled by the drawer via CSS, never JSX-conditional) so the tick
 * fan-out stays alive while the tab is visually hidden — the same rule
 * `TimeseriesChart` follows there.
 */

import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { get as apiGet } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import { useStore } from "@/store";
import { StatChip } from "@/components/shell/StatChip";
import { BreakdownBar } from "@/components/inspect/BreakdownBar";
import { SOCIAL_ROLE_LABELS } from "@/components/map/mapLensLayers";
import type { GameEvent, JournalPayload, TimeseriesPayload } from "@/types/game";
import type { InspectionCompositionEntry } from "@/types/inspection";

interface EconomyDashboardProps {
  gameId: string;
}

/**
 * Wealth-by-role composition color, one per canonical `SocialRole`
 * (`src/babylon/models/enums/social.py`). `SOCIAL_ROLE_COLOR`
 * (`components/map/mapLensLayers.ts`) is an RGBA array for deck.gl map
 * layers, not reusable here as-is — `BreakdownBar` wants a Tailwind
 * `text-*` token — so this is a parallel mapping onto this app's existing
 * `--babylon-*` tokens, chosen to match their documented meaning
 * (`index.css`) where one exists: `cadre` is literally documented "Labor
 * aristocracy, info text"; `rent`/`heat` track the extraction family
 * (core/comprador bourgeoisie); `laser` matches the map lens's own
 * `carceral_enforcer` choice exactly ("THREAT"). An unrecognized role key
 * (a scenario emitting something outside the 8 canonical values) falls
 * back to `BreakdownBar`'s own default rather than a fabricated color.
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

interface WealthChartRow {
  tick: number;
  wealth: number | null;
}

function wealthChartRows(timeseries: TimeseriesPayload): WealthChartRow[] {
  return timeseries.ticks.map((tick, i) => ({ tick, wealth: timeseries.wealth[i] ?? null }));
}

type CrisisFetchState =
  { status: "loading" } | { status: "ok"; events: GameEvent[] } | { status: "error" };

/**
 * Fetch the full cross-tick journal once on mount and keep only
 * `crisis_phase_transition` rows, tick-ordered — the only wired crisis
 * signal (Wave 2 owner ruling). No store surface reads `/journal/` yet
 * (no `panels.journal` slice), so this owns its own one-shot fetch rather
 * than inventing a new tick-fanned-out panel for a single strip.
 *
 * The initial `"loading"` state is the `useState` default, not set
 * synchronously inside the effect (`useVerbTargets.ts`'s idiom) — the
 * effect's only job is to call `setState` from the async `.then()`
 * callback once the response lands. `apiGet` never throws (network/API
 * errors are normalized into its returned envelope), so no unhandled
 * -rejection guard is needed on the bare `.then()`.
 */
function useCrisisTimeline(gameId: string): CrisisFetchState {
  const [state, setState] = useState<CrisisFetchState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    apiGet<JournalPayload>(endpoints.journal.path({ id: gameId })).then((res) => {
      if (cancelled) return;
      if (res.status !== "ok") {
        setState({ status: "error" });
        return;
      }
      const crises = res.data.events
        .filter((e) => e.type === "crisis_phase_transition")
        .sort((a, b) => a.tick - b.tick);
      setState({ status: "ok", events: crises });
    });
    return () => {
      cancelled = true;
    };
  }, [gameId]);

  return state;
}

const SEVERITY_COLOR: Record<GameEvent["severity"], string> = {
  critical: "text-laser",
  warning: "text-heat",
  informational: "text-solidarity",
};

function CrisisTimeline({ gameId }: { gameId: string }): React.JSX.Element {
  const state = useCrisisTimeline(gameId);

  if (state.status === "loading") {
    return <p className="text-[11px] italic text-shroud">Loading crisis history…</p>;
  }
  if (state.status === "error") {
    return <p className="text-[11px] italic text-shroud">Crisis history unavailable.</p>;
  }
  if (state.events.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="crisis-timeline-empty">
        No crisis-phase transitions recorded yet.
      </p>
    );
  }

  return (
    <ol className="flex flex-col gap-1" data-testid="crisis-timeline">
      {state.events.map((e) => (
        <li
          key={e.id}
          data-testid={`crisis-row-${e.id}`}
          className="flex items-center gap-2 text-[11px]"
        >
          <span className="font-mono text-[9px] text-ash">T{e.tick}</span>
          <span className={SEVERITY_COLOR[e.severity]}>●</span>
          <span className="text-bone">{e.title || e.body || e.type}</span>
        </li>
      ))}
    </ol>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">{children}</p>;
}

export function EconomyDashboard({ gameId }: EconomyDashboardProps): React.JSX.Element {
  const data = useStore((s) => s.panels.economy.data);
  const loading = useStore((s) => s.panels.economy.loading);
  const error = useStore((s) => s.panels.economy.error);
  const fetchEconomy = useStore((s) => s.panels.economy.fetch);
  const setMounted = useStore((s) => s.panels.economy.setMounted);
  const timeseries = useStore((s) => s.panels.timeseries.data);

  useEffect(() => {
    setMounted(true);
    void fetchEconomy(gameId);
    return () => setMounted(false);
  }, [gameId, fetchEconomy, setMounted]);

  if (loading && data === null) {
    return <p className="p-3 text-[11px] text-ash">Loading economy…</p>;
  }
  if (error) {
    return (
      <p role="alert" className="p-3 text-[11px] text-laser">
        {error}
      </p>
    );
  }
  if (data === null) {
    return <p className="p-3 text-[11px] italic text-shroud">No economy data yet.</p>;
  }
  if (!data.has_data) {
    return (
      <p className="p-3 text-[11px] italic text-shroud" data-testid="economy-no-data">
        No economic activity recorded in this graph yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-2" data-testid="economy-dashboard">
      <div className="flex flex-wrap gap-1.5" data-testid="economy-stat-chips">
        <StatChip label="Tick" value={data.tick} format={(v) => v.toFixed(0)} />
        <StatChip label="Value Produced" value={data.value_produced} format={(v) => v.toFixed(1)} />
        <StatChip
          label="Rent Extracted"
          value={data.rent_extracted}
          format={(v) => v.toFixed(1)}
          colorClassName="text-rent"
        />
        <StatChip
          label="Exploitation"
          value={data.exploitation_rate}
          format={(v) => v.toFixed(3)}
          metric="exploitation_rate"
        />
        <StatChip
          label="Profit Rate"
          value={data.profit_rate}
          format={(v) => v.toFixed(3)}
          colorClassName="text-rupture"
          metric="profit_rate"
        />
        <StatChip label="OCC" value={data.occ} format={(v) => v.toFixed(2)} metric="occ" />
        <StatChip
          label="Rent Pool"
          value={data.imperial_rent_pool}
          format={(v) => v.toFixed(1)}
          colorClassName="text-rent"
          metric="imperial_rent"
        />
        <StatChip
          label="Super-Wage Rate"
          value={data.current_super_wage_rate}
          format={(v) => v.toFixed(2)}
          colorClassName="text-cadre"
        />
        <StatChip
          label="Wage Flow"
          value={data.wage_flow_total}
          format={(v) => v.toFixed(1)}
          colorClassName="text-cadre"
        />
        <StatChip
          label="Tribute Flow"
          value={data.tribute_flow_total}
          format={(v) => v.toFixed(1)}
          colorClassName="text-rent"
        />
      </div>

      <div>
        <SectionLabel>Wealth by Class</SectionLabel>
        <BreakdownBar entries={wealthCompositionEntries(data.wealth_by_class_role)} />
      </div>

      <div>
        <SectionLabel>Wealth Trajectory</SectionLabel>
        {timeseries === null || timeseries.ticks.length === 0 ? (
          <p className="text-[11px] italic text-shroud" data-testid="wealth-trajectory-empty">
            No wealth trajectory yet.
          </p>
        ) : (
          <div className="h-24" data-testid="wealth-trajectory-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={wealthChartRows(timeseries)}>
                <XAxis dataKey="tick" tick={{ fontSize: 9, fill: "var(--babylon-ash)" }} />
                <YAxis tick={{ fontSize: 9, fill: "var(--babylon-ash)" }} />
                <Tooltip
                  contentStyle={{
                    background: "var(--babylon-concrete)",
                    border: "1px solid var(--babylon-rebar)",
                    fontSize: 11,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="wealth"
                  stroke="var(--babylon-population)"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div>
        <SectionLabel>Crisis Timeline</SectionLabel>
        <CrisisTimeline gameId={gameId} />
      </div>
    </div>
  );
}
