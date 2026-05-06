/**
 * OrgsPage — player action surface with org roster + 3×3 verb grid.
 *
 * Layout: left player roster (300px), right org detail + verb grid.
 * Only player-controlled orgs appear here.
 * Enemy orgs are accessed via Intel.
 */

import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { PageHeader } from "@/components/layout/PageHeader";
import { BblPanel, BblBadge, BblLabel, BblData, BblTooltip, Stat, Gauge } from "@/components/bbl";
import { ORGS, VERBS, COMMUNITIES, Scope } from "@/fixtures/v2-mock-data";
import { CLASS_COLORS } from "@/fixtures/v2-mock-data";

export function OrgsPage() {
  const navigate = useNavigate();
  const { id: gameId } = useParams<{ id: string }>();
  const playerOrgs = ORGS.filter((o) => o.player_controlled);
  const [activeOrgId, setActiveOrgId] = useState(playerOrgs[0]?.id ?? "");
  const org = ORGS.find((o) => o.id === activeOrgId);
  const v = org?.vanguard;

  // Communities this org participates in
  const orgCommunities = COMMUNITIES.filter((c) => org?.members.includes(c.id));

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Organizations"
        subtitle="Player action surface — select your org, choose a verb"
        breadcrumbs={["Operation", "Organizations"]}
        right={<BblBadge color="#40c040">{playerOrgs.length} allied orgs</BblBadge>}
      />

      <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr] gap-3 p-3">
        {/* Left: Player org roster */}
        <BblPanel title="Your Orgs" right={<BblLabel>select</BblLabel>}>
          <div className="flex flex-col gap-2">
            {playerOrgs.map((o) => {
              const isActive = o.id === activeOrgId;
              return (
                <button
                  key={o.id}
                  onClick={() => setActiveOrgId(o.id)}
                  className={`rounded-md border p-3 text-left transition-colors ${
                    isActive
                      ? "border-gold bg-gold/10"
                      : "border-soot bg-void hover:border-wet-concrete"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-bone">{o.short}</span>
                    <BblBadge color={CLASS_COLORS[o.class_character]}>{o.class_character}</BblBadge>
                  </div>
                  <div className="mt-1 text-[10px] text-ash">{o.name}</div>
                  {o.vanguard && (
                    <div className="mt-2 flex gap-3 font-mono text-[9px]">
                      <span className="text-royal-blue">{o.vanguard.cl} CL</span>
                      <span className="text-data-green">{o.vanguard.sl} SL</span>
                      <span className="text-gold">${o.vanguard.budget}</span>
                    </div>
                  )}
                </button>
              );
            })}

            {/* Note: enemy orgs go to Intel */}
            <div className="mt-2 rounded border border-dashed border-chassis p-2 text-center text-[10px] text-ash">
              Enemy orgs visible in <span className="text-gold">Intel</span> →
            </div>
          </div>
        </BblPanel>

        {/* Right: Selected org detail + verb grid */}
        <div className="flex min-h-0 flex-col gap-3">
          {/* Org detail header */}
          {org && (
            <BblPanel
              title={org.short}
              accent="#c8a860"
              right={
                <div className="flex items-center gap-2">
                  <BblBadge color="#80b0e0">{org.ooda_phase}</BblBadge>
                  {org.badges.map((b) => (
                    <BblBadge key={b} color="#787878">
                      {b}
                    </BblBadge>
                  ))}
                </div>
              }
            >
              <div className="flex flex-col gap-4">
                {/* Stats row */}
                <div className="flex gap-6">
                  <BblTooltip
                    text="Organizational unity"
                    breakdown={Scope.getScriptValueBreakdown("cohesion")}
                    total={org.cohesion}
                  >
                    <Stat
                      label="Cohesion"
                      value={`${(org.cohesion * 100).toFixed(0)}%`}
                      color="#c8a860"
                      wrap={false}
                    />
                  </BblTooltip>
                  <Stat
                    label="Legitimacy"
                    value={`${(org.legitimacy * 100).toFixed(0)}%`}
                    color="#40c040"
                  />
                  <Stat
                    label="Opacity"
                    value={`${(org.opacity * 100).toFixed(0)}%`}
                    color="#a070d0"
                  />
                  <BblTooltip
                    text="State repression exposure"
                    breakdown={Scope.getScriptValueBreakdown("heat")}
                    total={v?.heat ?? 0}
                  >
                    <Stat
                      label="Heat"
                      value={`${((v?.heat ?? 0) * 100).toFixed(0)}%`}
                      color="#e04040"
                      wrap={false}
                    />
                  </BblTooltip>
                </div>

                {/* Vanguard gauges */}
                {v && (
                  <div className="flex gap-4">
                    <Gauge label="CL" value={v.cl} max={v.cl_max} color="#80b0e0" />
                    <Gauge label="SL" value={v.sl} max={v.sl_max} color="#40c040" />
                    <div className="flex flex-col gap-1">
                      <div className="flex items-baseline gap-1">
                        <BblLabel>REP</BblLabel>
                        <BblData size={10}>{(v.rep * 100).toFixed(0)}%</BblData>
                      </div>
                      <div className="flex items-baseline gap-1">
                        <BblLabel>Budget</BblLabel>
                        <BblData size={10} color="#c8a860">
                          ${v.budget}
                        </BblData>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </BblPanel>
          )}

          {/* Bottom: Verb grid + Communities */}
          <div className="grid min-h-0 flex-1 grid-cols-[1fr_1fr] gap-3">
            {/* 3×3 Verb Grid */}
            <BblPanel title="Actions" right={<BblLabel>9 verbs</BblLabel>}>
              <div className="grid grid-cols-3 gap-2">
                {VERBS.map((verb) => (
                  <button
                    key={verb.verb}
                    onClick={() => navigate(`/games/${gameId}/actions/${verb.verb}`)}
                    className="flex flex-col items-center gap-1 rounded-md border border-soot bg-void p-3 text-ash transition-all hover:border-gold hover:text-gold"
                  >
                    <span className="text-lg">{verb.glyph}</span>
                    <span className="text-[9px] font-semibold uppercase tracking-wider">
                      {verb.label}
                    </span>
                    <span className="text-[8px] text-chassis">{verb.cost_label}</span>
                  </button>
                ))}
              </div>
            </BblPanel>

            {/* Community memberships */}
            <BblPanel
              title="Communities"
              right={<BblBadge color="#787878">{orgCommunities.length}</BblBadge>}
            >
              <div className="flex flex-col gap-2">
                {orgCommunities.map((c) => (
                  <div key={c.id} className="rounded border border-soot bg-void p-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-bone">{c.name}</span>
                      <BblBadge color={CLASS_COLORS[c.dominant_class]}>{c.dominant_class}</BblBadge>
                    </div>
                    <div className="mt-1 text-[9px] text-ash">
                      {c.composition.join(" · ")} · {c.members.toLocaleString()} ppl
                    </div>
                    <div className="mt-1 flex gap-3 font-mono text-[9px]">
                      <span className="text-royal-blue">CON {(c.con * 100).toFixed(0)}%</span>
                      <span className="text-data-green">SOL {(c.sol * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </BblPanel>
          </div>
        </div>
      </div>
    </div>
  );
}
