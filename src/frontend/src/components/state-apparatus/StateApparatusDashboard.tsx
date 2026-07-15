/**
 * StateApparatusDashboard — the `/state-apparatus/` BottomDrawer tab
 * (spec-111 C2). This is where the player watches "the Blind Giant" act:
 * wayne_county seeds the Detroit Police Department (`ORG002`, a real
 * `state_apparatus` org) and the `RuleBasedStateAI` drives it every tick —
 * surveilling and repressing organizations. This dashboard surfaces its
 * repression budget, accumulated heat, seeded state org(s), and recent
 * STATE_REPRESSION/STATE_SURVEILLANCE/STATE_ACTION_EXECUTED actions.
 *
 * Mirrors `EconomyDashboard` (Wave 2 W2.2a) exactly: same panel shape
 * (`panels.stateApparatus`, `PANEL_KEYS`-fanned-out), same
 * setMounted(true)/fetch-on-mount/setMounted(false)-on-unmount idiom, same
 * `BottomDrawer` tab-row mechanism (`ui.chrome.bottomDrawer`'s
 * `"state-apparatus"` arm) rather than a new UI location. Unlike
 * `EconomyDashboard`'s crisis timeline (which needs its own `/journal/`
 * fetch since the economy payload carries no events), `recent_actions`
 * arrives inside this endpoint's own payload — no second fetch required.
 *
 * Honest-null throughout (Constitution III.11): `organizations`/
 * `recent_actions` may legitimately be empty (a fresh session before any
 * tick has run the state AI), and `state_finances` is empty for every
 * scenario shipped today (no scenario seeds `WorldState.state_finances`
 * yet) — all three render an explicit "no data yet" message, never a
 * fabricated placeholder.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { StatChip } from "@/components/shell/StatChip";
import type { GameEvent, OrgState } from "@/types/game";

interface StateApparatusDashboardProps {
  gameId: string;
}

function SectionLabel({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">{children}</p>;
}

/**
 * The seeded state-apparatus org(s) — id/name/budget/heat. Reuses `OrgState`
 * verbatim (the same shape the Outliner/OrgNetwork already render); no new
 * type invented for what's already a first-class entity elsewhere.
 */
function StateOrgList({ organizations }: { organizations: OrgState[] }): React.JSX.Element {
  if (organizations.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="state-apparatus-orgs-empty">
        No state apparatus organizations seeded this session.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-1" data-testid="state-apparatus-orgs">
      {organizations.map((org) => (
        <li
          key={org.id}
          data-testid={`state-org-${org.id}`}
          className="flex items-center gap-2 text-[11px]"
        >
          <span className="flex-1 truncate text-bone">{org.name}</span>
          <span className="font-mono text-[9px] text-ash">{org.id}</span>
          <span className="font-mono text-[10px] text-laser">budget {org.budget.toFixed(1)}</span>
          <span className="font-mono text-[10px] text-heat">heat {org.heat.toFixed(2)}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * `state_finances` is honestly `{}` today (no scenario seeds
 * `WorldState.state_finances` — see the payload's docstring). Rendered
 * generically (state ids only, no invented field shape) so a future seeded
 * session degrades gracefully instead of needing a rewrite.
 */
function StateFinances({ finances }: { finances: Record<string, unknown> }): React.JSX.Element {
  const stateIds = Object.keys(finances);

  if (stateIds.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="state-finances-empty">
        No state finances seeded this session.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-1" data-testid="state-finances">
      {stateIds.map((stateId) => (
        <li key={stateId} className="font-mono text-[11px] text-bone">
          {stateId}
        </li>
      ))}
    </ul>
  );
}

const SEVERITY_COLOR: Record<GameEvent["severity"], string> = {
  critical: "text-laser",
  warning: "text-heat",
  informational: "text-solidarity",
};

/** Recent STATE_REPRESSION/STATE_SURVEILLANCE/STATE_ACTION_EXECUTED events —
 *  same compact tick + severity-dot + title row `EconomyDashboard`'s
 *  crisis timeline uses, reusing `GameEvent` verbatim. */
function ActionFeed({ actions }: { actions: GameEvent[] }): React.JSX.Element {
  if (actions.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="state-actions-empty">
        No state actions this session yet.
      </p>
    );
  }

  return (
    <ol className="flex flex-col gap-1" data-testid="state-actions-feed">
      {actions.map((e) => (
        <li
          key={e.id}
          data-testid={`state-action-${e.id}`}
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

export function StateApparatusDashboard({
  gameId,
}: StateApparatusDashboardProps): React.JSX.Element {
  const data = useStore((s) => s.panels.stateApparatus.data);
  const loading = useStore((s) => s.panels.stateApparatus.loading);
  const error = useStore((s) => s.panels.stateApparatus.error);
  const fetchStateApparatus = useStore((s) => s.panels.stateApparatus.fetch);
  const setMounted = useStore((s) => s.panels.stateApparatus.setMounted);

  useEffect(() => {
    setMounted(true);
    void fetchStateApparatus(gameId);
    return () => setMounted(false);
  }, [gameId, fetchStateApparatus, setMounted]);

  if (loading && data === null) {
    return <p className="p-3 text-[11px] text-ash">Loading state apparatus…</p>;
  }
  if (error) {
    return (
      <p role="alert" className="p-3 text-[11px] text-laser">
        {error}
      </p>
    );
  }
  if (data === null) {
    return (
      <p className="p-3 text-[11px] italic text-shroud" data-testid="state-apparatus-no-data">
        No state apparatus data yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-2" data-testid="state-apparatus-dashboard">
      <div className="flex flex-wrap gap-1.5" data-testid="state-apparatus-stat-chips">
        <StatChip
          label="Repression Budget"
          value={data.total_repression_budget}
          format={(v) => v.toFixed(1)}
          colorClassName="text-laser"
        />
        <StatChip
          label="Total Heat"
          value={data.total_heat}
          format={(v) => v.toFixed(2)}
          colorClassName="text-heat"
        />
        <StatChip label="Org Count" value={data.org_count} format={(v) => v.toFixed(0)} />
      </div>

      <div>
        <SectionLabel>State Apparatus Organizations</SectionLabel>
        <StateOrgList organizations={data.organizations} />
      </div>

      <div>
        <SectionLabel>State Finances</SectionLabel>
        <StateFinances finances={data.state_finances} />
      </div>

      <div>
        <SectionLabel>Recent Actions</SectionLabel>
        <ActionFeed actions={data.recent_actions} />
      </div>
    </div>
  );
}
