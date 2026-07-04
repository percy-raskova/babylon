/**
 * OrgDetailView — full organization drill-down (spec 093 US2).
 *
 * Ported from `design/mockups/ui_kits/webapp/OrgDetail.jsx`'s layout onto
 * live `GameSnapshot` data: vanguard economy stats, OODA phase, a
 * relations list derived from real edge `mode` (not a random ally/hostile
 * label), and events actually referencing the organization. Every numeric
 * stat is wrapped in `BreakdownTooltip` for provenance (FR-010/FR-012).
 */

import { BblBadge, BblData, BblPanel, Stat } from "@/components/bbl";
import { BreakdownTooltip } from "@/components/inspector/BreakdownTooltip";
import { selectors } from "@/lib/selectors";
import type { Scope } from "@/lib/selectors";
import type { EdgeMode, EdgeState, GameSnapshot, OrgState } from "@/types/game";

interface OrgDetailViewProps {
  org: OrgState;
  snapshot: GameSnapshot;
  edges: EdgeState[];
}

interface Relation {
  otherId: string;
  otherName: string;
  mode: EdgeMode;
}

/** Real (non-random) relation classification: the edge's actual `mode`. */
function relationsFor(org: OrgState, snapshot: GameSnapshot, edges: EdgeState[]): Relation[] {
  const relations: Relation[] = [];
  for (const edge of edges) {
    let otherId: string | null = null;
    if (edge.source_id === org.id) otherId = edge.target_id;
    else if (edge.target_id === org.id) otherId = edge.source_id;
    if (!otherId) continue;
    const other = snapshot.organizations.find((o) => o.id === otherId);
    relations.push({
      otherId,
      otherName: other?.short_name ?? other?.name ?? otherId,
      mode: edge.mode,
    });
  }
  return relations;
}

/** Real (non-random) org-scoped events: matches on any org-shaped
 * reference the event's data payload carries. */
function eventsForOrg(snapshot: GameSnapshot, orgId: string) {
  return snapshot.events.filter((e) => {
    const data = e.data as Record<string, unknown>;
    return data.org_id === orgId || data.source_id === orgId || data.target_id === orgId;
  });
}

const RELATION_COLOR: Record<EdgeMode, string> = {
  SOLIDARISTIC: "#5fbf7a",
  ANTAGONISTIC: "#e04040",
  CO_OPTIVE: "#a070d0",
  EXTRACTIVE: "#a070d0",
  TRANSACTIONAL: "#787878",
};

function StatWithBreakdown({
  selectorName,
  scope,
  value,
  color,
}: {
  selectorName: string;
  scope: Scope;
  value: string;
  color: string;
}) {
  const selector = selectors.get(selectorName);
  return (
    <BreakdownTooltip selector={selector} scope={scope}>
      <Stat label={selector.label} value={value} color={color} wrap={false} />
    </BreakdownTooltip>
  );
}

export function OrgDetailView({ org, snapshot, edges }: OrgDetailViewProps) {
  const scope: Scope = { snapshot, this: { kind: "org", id: org.id } };
  const relations = relationsFor(org, snapshot, edges);
  const events = eventsForOrg(snapshot, org.id);
  const vanguard = org.vanguard;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline gap-3">
        <h2 className="text-xl font-bold text-bone">{org.short_name ?? org.name}</h2>
        <BblBadge color="#787878">{org.org_type}</BblBadge>
        <BblBadge color="#787878">{org.class_character}</BblBadge>
        <span className="ml-auto text-[10px] text-ash">
          OODA: <span className="text-spire">{org.ooda.phase ?? "observe"}</span>
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <StatWithBreakdown
          selectorName="org.cohesion"
          scope={scope}
          value={`${(org.cohesion * 100).toFixed(0)}%`}
          color="#c8a860"
        />
        <StatWithBreakdown
          selectorName="org.heat"
          scope={scope}
          value={`${(org.heat * 100).toFixed(0)}%`}
          color="#e04040"
        />
        <StatWithBreakdown
          selectorName="org.opacity"
          scope={scope}
          value={`${((org.opacity ?? 0) * 100).toFixed(0)}%`}
          color="#a070d0"
        />
      </div>

      <BblPanel title="Vanguard Economy" accent="#c8a860">
        {!vanguard ? (
          <div className="text-[11px] text-ash">
            No vanguard economy data (not a player-controlled organization).
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-3">
            <StatWithBreakdown
              selectorName="org.vanguard_cadre_labor"
              scope={scope}
              value={`${vanguard.cadre_labor.toFixed(1)} / ${vanguard.max_cadre_labor}`}
              color="#c8a860"
            />
            <StatWithBreakdown
              selectorName="org.vanguard_sympathizer_labor"
              scope={scope}
              value={`${vanguard.sympathizer_labor.toFixed(1)} / ${vanguard.max_sympathizer_labor}`}
              color="#5fbf7a"
            />
            <StatWithBreakdown
              selectorName="org.vanguard_reputation"
              scope={scope}
              value={`${(vanguard.reputation * 100).toFixed(0)}%`}
              color="#80b0e0"
            />
            <StatWithBreakdown
              selectorName="org.budget"
              scope={scope}
              value={vanguard.budget.toFixed(1)}
              color="#e04040"
            />
          </div>
        )}
      </BblPanel>

      <div className="grid grid-cols-2 gap-3">
        <BblPanel title="Relations" accent="#2a2a3a">
          {relations.length === 0 ? (
            <div className="text-[11px] text-ash">No known relations.</div>
          ) : (
            <div className="flex flex-col gap-2">
              {relations.map((r) => (
                <div
                  key={`${r.otherId}-${r.mode}`}
                  className="flex items-center justify-between text-[12px]"
                >
                  <span className="text-bone">{r.otherName}</span>
                  <BblBadge color={RELATION_COLOR[r.mode]}>{r.mode.toLowerCase()}</BblBadge>
                </div>
              ))}
            </div>
          )}
        </BblPanel>

        <BblPanel title="Org History" accent="#2a2a3a">
          {events.length === 0 ? (
            <div className="text-[11px] text-ash">No recorded history yet.</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {events.slice(0, 6).map((e) => (
                <div key={e.id} className="flex gap-2 text-[11px]">
                  <BblData size={10}>t={e.tick}</BblData>
                  <span className="text-ash">{e.title}</span>
                </div>
              ))}
            </div>
          )}
        </BblPanel>
      </div>
    </div>
  );
}
