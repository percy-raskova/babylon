/**
 * ResultsPage — tick resolution summary.
 *
 * Spec 061 US6 (T102): replaces the v2-mock-data import with the
 * live snapshot. The hardcoded tensor-diff panel from the prior
 * fixture-driven design is dropped (spec 061 plan.md Out of Scope:
 * the d3-force topology + tensor-diff panels are deferred to a
 * v2-pages-polish follow-up spec).
 */

import { useParams } from "react-router";
import { BblBadge, BblPanel } from "@/components/bbl";
import { PageHeader } from "@/components/layout/PageHeader";
import { useGameState } from "@/hooks/useGameState";

export function ResultsPage() {
  const { id: gameId } = useParams<{ id: string }>();
  const { snapshot } = useGameState(gameId ?? null);
  const tick = snapshot?.tick ?? 0;
  const orgs = snapshot?.organizations ?? [];
  const playerOrgs = orgs.filter((o) => Boolean(o.player_controlled));
  const npcOrgs = orgs.filter((o) => !o.player_controlled);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Results"
        subtitle={`Tick ${tick} resolution summary`}
        breadcrumbs={["Operation", "Results"]}
        right={<BblBadge color="#787878">read-only</BblBadge>}
      />

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3 p-3">
        {/* Player roster */}
        <BblPanel title="Player Orgs" accent="#c8a860">
          <div className="flex flex-col gap-2">
            {playerOrgs.length === 0 && (
              <div className="rounded border border-dashed border-chassis p-3 text-center text-[10px] text-ash">
                No player orgs in this session.
              </div>
            )}
            {playerOrgs.map((o) => (
              <div key={o.id} className="rounded border border-soot bg-void p-2">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-bone">
                    {o.short_name ?? o.name}
                  </span>
                  <BblBadge color="#80b0e0">{o.ooda?.phase ?? "observe"}</BblBadge>
                </div>
                <div className="mt-1 text-[9px] text-ash">
                  COH {(o.cohesion * 100).toFixed(0)}% · HEAT {(o.heat * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </BblPanel>

        {/* NPC roster */}
        <BblPanel title="NPC Orgs" accent="#787878">
          <div className="flex flex-col gap-2">
            {npcOrgs.length === 0 && (
              <div className="rounded border border-dashed border-chassis p-3 text-center text-[10px] text-ash">
                No NPC orgs surfaced.
              </div>
            )}
            {npcOrgs.map((o) => (
              <div key={o.id} className="rounded border border-soot bg-void p-2">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-bone">
                    {o.short_name ?? o.name}
                  </span>
                  <BblBadge color="#787878">{o.ooda?.phase ?? "observe"}</BblBadge>
                </div>
                <div className="mt-1 text-[9px] text-ash">
                  COH {(o.cohesion * 100).toFixed(0)}% · class {o.class_character}
                </div>
              </div>
            ))}
          </div>
        </BblPanel>
      </div>
    </div>
  );
}
