/**
 * IntelPageV2 — 4-variant inspector for surveillance targets.
 *
 * Left panel: surveillance index with category tabs (Territories, Orgs, Edges, Communities).
 * Right panel: detail inspector that renders based on targetType URL param.
 *
 * Variants:
 *   /intel                        — index view, pick a target
 *   /intel/org/:id                — enemy org dossier
 *   /intel/territory/:id          — territory stats + community list
 *   /intel/edge/:id               — edge source→target with intensity
 *   /intel/community/:id          — composition, credibility, stats
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router";
import { PageHeader } from "@/components/layout/PageHeader";
import { BblPanel, BblBadge, BblLabel, BblData, Stat } from "@/components/bbl";
import {
  ORGS,
  TERRITORIES,
  COMMUNITIES,
  EDGES,
  Scope,
  CLASS_COLORS,
  EDGE_COLORS,
} from "@/fixtures/v2-mock-data";

type IntelTab = "territories" | "orgs" | "edges" | "communities";

export function IntelPageV2() {
  const {
    id: gameId,
    targetType,
    targetId,
  } = useParams<{
    id: string;
    targetType: string;
    targetId: string;
  }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<IntelTab>("territories");

  const tabs: { key: IntelTab; label: string; count: number }[] = [
    { key: "territories", label: "Territories", count: TERRITORIES.length },
    { key: "orgs", label: "Orgs", count: ORGS.filter((o) => !o.player_controlled).length },
    { key: "edges", label: "Edges", count: EDGES.length },
    { key: "communities", label: "Communities", count: COMMUNITIES.length },
  ];

  function navTo(type: string, id: string) {
    navigate(`/games/${gameId}/intel/${type}/${id}`);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Intel"
        subtitle="Surveillance index — inspect targets across the social graph"
        breadcrumbs={["Operation", "Intel", ...(targetType ? [targetType] : [])]}
        right={<BblBadge color="#a070d0">read + act</BblBadge>}
      />

      <div className="grid min-h-0 flex-1 grid-cols-[260px_1fr] gap-3 p-3">
        <BblPanel title="Surveillance Index">
          <TabStrip tabs={tabs} active={tab} onSelect={setTab} />
          <EntityIndex tab={tab} targetId={targetId} onSelect={navTo} />
        </BblPanel>
        <div className="min-h-0 overflow-auto">
          <DetailDispatcher
            targetType={targetType}
            targetId={targetId ?? ""}
            gameId={gameId ?? ""}
          />
        </div>
      </div>
    </div>
  );
}

interface TabSpec {
  key: IntelTab;
  label: string;
  count: number;
}

function TabStrip({
  tabs,
  active,
  onSelect,
}: {
  tabs: TabSpec[];
  active: IntelTab;
  onSelect: (key: IntelTab) => void;
}) {
  return (
    <div className="mb-3 flex gap-1">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onSelect(t.key)}
          className={`flex-1 rounded border px-1 py-1.5 text-[8px] uppercase tracking-wider ${
            active === t.key
              ? "border-gold bg-gold/10 text-gold"
              : "border-soot text-ash hover:text-bone"
          }`}
        >
          {t.label}
          <span className="ml-0.5 text-chassis">({t.count})</span>
        </button>
      ))}
    </div>
  );
}

function EntityIndex({
  tab,
  targetId,
  onSelect,
}: {
  tab: IntelTab;
  targetId: string | undefined;
  onSelect: (type: string, id: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      {tab === "territories" &&
        TERRITORIES.map((t) => (
          <IndexRow
            key={t.id}
            label={t.name}
            sub={`${t.county} · pop ${t.pop.toLocaleString()}`}
            color="#80b0e0"
            active={targetId === t.id}
            onClick={() => onSelect("territory", t.id)}
          />
        ))}
      {tab === "orgs" &&
        ORGS.filter((o) => !o.player_controlled).map((o) => (
          <IndexRow
            key={o.id}
            label={o.short}
            sub={`${o.name} · ${o.threat_level ?? "?"}`}
            color={CLASS_COLORS[o.class_character] ?? "#787878"}
            active={targetId === o.id}
            onClick={() => onSelect("org", o.id)}
          />
        ))}
      {tab === "edges" &&
        EDGES.map((e) => (
          <IndexRow
            key={e.id}
            label={e.type}
            sub={`${e.source} → ${e.target}`}
            color={EDGE_COLORS[e.type] ?? "#787878"}
            active={targetId === e.id}
            onClick={() => onSelect("edge", e.id)}
          />
        ))}
      {tab === "communities" &&
        COMMUNITIES.map((c) => (
          <IndexRow
            key={c.id}
            label={c.name}
            sub={`${c.members.toLocaleString()} members`}
            color={CLASS_COLORS[c.dominant_class] ?? "#787878"}
            active={targetId === c.id}
            onClick={() => onSelect("community", c.id)}
          />
        ))}
    </div>
  );
}

function DetailDispatcher({
  targetType,
  targetId,
  gameId,
}: {
  targetType: string | undefined;
  targetId: string;
  gameId: string;
}) {
  if (!targetType) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ash">
        Select a target from the index to inspect
      </div>
    );
  }
  if (targetType === "org") return <OrgDetail id={targetId} gameId={gameId} />;
  if (targetType === "territory") return <TerritoryDetail id={targetId} gameId={gameId} />;
  if (targetType === "edge") return <EdgeDetail id={targetId} />;
  if (targetType === "community") return <CommunityDetail id={targetId} gameId={gameId} />;
  return <NoData label="Unknown target type" id={targetType} />;
}

// --- Index row ---
function IndexRow({
  label,
  sub,
  color,
  active,
  onClick,
}: {
  label: string;
  sub: string;
  color: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 rounded border p-2 text-left ${
        active ? "border-gold bg-gold/8" : "border-soot bg-void hover:border-wet-concrete"
      }`}
    >
      <div className="h-6 w-1 shrink-0 rounded-full" style={{ background: color }} />
      <div className="min-w-0">
        <div className="truncate text-[11px] font-semibold text-bone">{label}</div>
        <div className="truncate text-[9px] text-ash">{sub}</div>
      </div>
    </button>
  );
}

// --- Org Detail Variant ---
function OrgDetail({ id, gameId }: { id: string; gameId: string }) {
  const navigate = useNavigate();
  const org = Scope.getOrg(id);
  if (!org) return <NoData label="Org" id={id} />;
  const edges = Scope.getEdgesOf(id);

  return (
    <BblPanel
      title={org.short}
      accent={CLASS_COLORS[org.class_character] ?? "#787878"}
      right={
        <div className="flex gap-1">
          <BblBadge color={CLASS_COLORS[org.class_character]}>{org.class_character}</BblBadge>
          <BblBadge color="#80b0e0">{org.ooda_phase}</BblBadge>
          {org.threat_level && <BblBadge color="#e04040">{org.threat_level}</BblBadge>}
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="text-[12px] text-bone">{org.name}</div>
        <div className="text-[10px] text-ash">
          HQ: {org.hq_territory} · Type: {org.org_type}
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-4 gap-4">
          <Stat label="Cohesion" value={`${(org.cohesion * 100).toFixed(0)}%`} color="#c8a860" />
          <Stat
            label="Legitimacy"
            value={`${(org.legitimacy * 100).toFixed(0)}%`}
            color="#40c040"
          />
          <Stat label="Opacity" value={`${(org.opacity * 100).toFixed(0)}%`} color="#a070d0" />
          <Stat
            label="Observed"
            value={org.last_observed_tick ? `T-${org.last_observed_tick}` : "—"}
            color="#787878"
          />
        </div>

        {/* Edges */}
        {edges.length > 0 && (
          <div>
            <BblLabel color="#c8a860">Edges ({edges.length})</BblLabel>
            <div className="mt-2 flex flex-col gap-1">
              {edges.map((e) => (
                <button
                  key={e.id}
                  onClick={() => navigate(`/games/${gameId}/intel/edge/${e.id}`)}
                  className="flex items-center gap-2 rounded border border-soot bg-void p-2 text-left hover:border-wet-concrete"
                >
                  <BblBadge color={EDGE_COLORS[e.type]}>{e.type}</BblBadge>
                  <span className="text-[10px] text-ash">
                    {e.source} → {e.target}
                  </span>
                  <BblData size={9} color={EDGE_COLORS[e.type]}>
                    {(e.intensity * 100).toFixed(0)}%
                  </BblData>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/games/${gameId}/actions/investigate`)}
            className="rounded border border-gold px-3 py-1.5 text-[10px] text-gold hover:bg-gold/10"
          >
            ◉ Investigate
          </button>
          <button
            onClick={() => navigate(`/games/${gameId}/actions/attack`)}
            className="rounded border border-crimson px-3 py-1.5 text-[10px] text-crimson hover:bg-crimson/10"
          >
            ▲ Attack
          </button>
        </div>
      </div>
    </BblPanel>
  );
}

// --- Territory Detail Variant ---
function TerritoryDetail({ id, gameId }: { id: string; gameId: string }) {
  const navigate = useNavigate();
  const terr = Scope.getTerritory(id);
  if (!terr) return <NoData label="Territory" id={id} />;
  const communities = Scope.getCommunitiesIn(id);

  return (
    <BblPanel
      title={terr.name}
      accent="#80b0e0"
      right={<BblBadge color="#787878">{terr.county} County</BblBadge>}
    >
      <div className="flex flex-col gap-4">
        {/* Stats grid */}
        <div className="grid grid-cols-4 gap-4">
          <Stat label="Population" value={terr.pop.toLocaleString()} color="#80b0e0" />
          <Stat label="Heat" value={`${(terr.heat * 100).toFixed(0)}%`} color="#e04040" />
          <Stat label="Rent" value={`${(terr.rent * 100).toFixed(0)}%`} color="#a070d0" />
          <Stat label="Consciousness" value={`${(terr.con * 100).toFixed(0)}%`} color="#80b0e0" />
        </div>
        <div className="grid grid-cols-4 gap-4">
          <Stat label="Solidarity" value={`${(terr.sol * 100).toFixed(0)}%`} color="#40c040" />
          <Stat label="Wealth" value={`${(terr.wealth * 100).toFixed(0)}%`} color="#c8a860" />
          <Stat label="Biocapacity" value={`${(terr.biocap * 100).toFixed(0)}%`} color="#7ab038" />
          <Stat label="Dominant" value={terr.dominant_community} color="#787878" />
        </div>

        {/* Communities in territory */}
        {communities.length > 0 && (
          <div>
            <BblLabel color="#c8a860">Communities ({communities.length})</BblLabel>
            <div className="mt-2 flex flex-col gap-1">
              {communities.map((c) => (
                <button
                  key={c.id}
                  onClick={() => navigate(`/games/${gameId}/intel/community/${c.id}`)}
                  className="flex items-center justify-between rounded border border-soot bg-void p-2 text-left hover:border-wet-concrete"
                >
                  <div>
                    <span className="text-[11px] font-semibold text-bone">{c.name}</span>
                    <div className="mt-0.5 flex gap-1">
                      {c.composition.map((tag) => (
                        <BblBadge key={tag} color={CLASS_COLORS[c.dominant_class]}>
                          {tag}
                        </BblBadge>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-3 font-mono text-[9px]">
                    <span className="text-royal-blue">CON {(c.con * 100).toFixed(0)}%</span>
                    <span className="text-data-green">SOL {(c.sol * 100).toFixed(0)}%</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/games/${gameId}/actions/move`)}
            className="rounded border border-gold px-3 py-1.5 text-[10px] text-gold hover:bg-gold/10"
          >
            → Move Here
          </button>
          <button
            onClick={() => navigate(`/games/${gameId}/actions/campaign`)}
            className="rounded border border-gold px-3 py-1.5 text-[10px] text-gold hover:bg-gold/10"
          >
            ◢ Campaign
          </button>
        </div>
      </div>
    </BblPanel>
  );
}

// --- Edge Detail Variant ---
function EdgeDetail({ id }: { id: string }) {
  const edge = Scope.getEdge(id);
  if (!edge) return <NoData label="Edge" id={id} />;

  return (
    <BblPanel
      title={edge.type}
      accent={EDGE_COLORS[edge.type] ?? "#787878"}
      right={<BblBadge color={EDGE_COLORS[edge.type]}>{edge.type}</BblBadge>}
    >
      <div className="flex flex-col gap-4">
        {/* Source → Target */}
        <div className="flex items-center gap-3 rounded border border-soot bg-void p-3">
          <div className="rounded bg-soot px-2 py-1 text-[11px] font-semibold text-bone">
            {edge.source}
          </div>
          <span className="text-gold">→</span>
          <div className="rounded bg-soot px-2 py-1 text-[11px] font-semibold text-bone">
            {edge.target}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Stat
            label="Intensity"
            value={`${(edge.intensity * 100).toFixed(0)}%`}
            color={EDGE_COLORS[edge.type] ?? "#787878"}
          />
          {edge.rate_of_profit !== undefined && (
            <Stat
              label="Rate of Profit"
              value={`${(edge.rate_of_profit * 100).toFixed(0)}%`}
              color="#c8a860"
            />
          )}
          {edge.rent_burden !== undefined && (
            <Stat
              label="Rent Burden"
              value={`${(edge.rent_burden * 100).toFixed(0)}%`}
              color="#a070d0"
            />
          )}
          {edge.value_flow_per_tick !== undefined && (
            <Stat label="Value Flow" value={`${edge.value_flow_per_tick}/tick`} color="#c8a860" />
          )}
          {edge.age_ticks !== undefined && (
            <Stat label="Age" value={`${edge.age_ticks} ticks`} color="#787878" />
          )}
        </div>

        {edge.last_event && (
          <div className="rounded border border-dashed border-crimson/30 bg-crimson/5 p-2 text-[10px] text-ash">
            Last event: <span className="text-crimson">{edge.last_event}</span>
          </div>
        )}
      </div>
    </BblPanel>
  );
}

// --- Community Detail Variant ---
function CommunityDetail({ id, gameId }: { id: string; gameId: string }) {
  const navigate = useNavigate();
  const comm = Scope.getCommunity(id);
  if (!comm) return <NoData label="Community" id={id} />;

  return (
    <BblPanel
      title={comm.name}
      accent={CLASS_COLORS[comm.dominant_class] ?? "#787878"}
      right={<BblBadge color={CLASS_COLORS[comm.dominant_class]}>{comm.dominant_class}</BblBadge>}
    >
      <div className="flex flex-col gap-4">
        {/* Composition badges */}
        <div className="flex flex-wrap gap-1">
          {comm.composition.map((tag) => (
            <BblBadge key={tag} color={CLASS_COLORS[comm.dominant_class]}>
              {tag}
            </BblBadge>
          ))}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4">
          <Stat label="Members" value={comm.members.toLocaleString()} color="#80b0e0" />
          <Stat label="Consciousness" value={`${(comm.con * 100).toFixed(0)}%`} color="#80b0e0" />
          <Stat label="Solidarity" value={`${(comm.sol * 100).toFixed(0)}%`} color="#40c040" />
          <Stat
            label="Dominant"
            value={comm.dominant_class}
            color={CLASS_COLORS[comm.dominant_class] ?? "#787878"}
          />
        </div>

        {/* Credibility to player orgs */}
        <div>
          <BblLabel color="#c8a860">Credibility to Player Orgs</BblLabel>
          <div className="mt-2 flex flex-col gap-2">
            {Object.entries(comm.credibility_to).map(([orgId, cred]) => {
              const org = Scope.getOrg(orgId);
              return (
                <div key={orgId} className="flex items-center gap-2">
                  <span className="w-16 text-[10px] font-semibold text-bone">
                    {org?.short ?? orgId}
                  </span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-soot">
                    <div
                      className="h-full rounded-full bg-gold"
                      style={{ width: `${cred * 100}%` }}
                    />
                  </div>
                  <BblData size={9}>{(cred * 100).toFixed(0)}%</BblData>
                </div>
              );
            })}
          </div>
        </div>

        {/* Territories */}
        <div className="text-[10px] text-ash">Territories: {comm.territories.join(", ")}</div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/games/${gameId}/actions/educate`)}
            className="rounded border border-gold px-3 py-1.5 text-[10px] text-gold hover:bg-gold/10"
          >
            ◐ Educate
          </button>
          <button
            onClick={() => navigate(`/games/${gameId}/actions/mobilize`)}
            className="rounded border border-gold px-3 py-1.5 text-[10px] text-gold hover:bg-gold/10"
          >
            ◈ Mobilize
          </button>
        </div>
      </div>
    </BblPanel>
  );
}

function NoData({ label, id }: { label: string; id: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-ash">
      {label} "{id}" not found
    </div>
  );
}
