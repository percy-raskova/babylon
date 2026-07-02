/**
 * IntelPageV2 — 4-variant inspector for surveillance targets.
 *
 * Spec 061 US6 (T101): wired to the live snapshot. The detail
 * inspectors render directly from the snapshot for territories /
 * orgs / edges; the communities variant renders the snapshot's
 * hyperedges (XGI community layer — label, category, material basis,
 * identity strength; local-play wire-up sprint 2026-07-02).
 */

import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { BblBadge, BblData, BblLabel, BblPanel, Stat } from "@/components/bbl";
import { PageHeader } from "@/components/layout/PageHeader";
import { useGameState } from "@/hooks/useGameState";
import type { HyperedgeState, OrgState } from "@/types/game";

type IntelTab = "territories" | "orgs" | "edges" | "communities";

interface SnapshotTerritory {
  id: string;
  name: string;
  county_fips?: string;
  heat: number;
  rent_level: number;
  population: number;
  consciousness?: number;
  solidarity?: number;
  wealth?: number;
  dominant_community?: string;
}

interface SnapshotEdge {
  id: string;
  source_id: string;
  target_id: string;
  mode: string;
  value_flow: number;
  tension: number;
  rate_of_profit?: number | null;
  rent_burden?: number | null;
  age_ticks?: number | null;
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded border border-dashed border-chassis p-3 text-center text-[10px] text-ash">
      {label}
    </div>
  );
}

interface IndexListProps {
  tab: IntelTab;
  territories: SnapshotTerritory[];
  orgs: OrgState[];
  edges: SnapshotEdge[];
  communities: HyperedgeState[];
  gameId: string | undefined;
  navigate: (path: string) => void;
}

function IndexList({
  tab,
  territories,
  orgs,
  edges,
  communities,
  gameId,
  navigate,
}: IndexListProps) {
  if (tab === "territories") {
    if (territories.length === 0) return <EmptyState label="No territories surfaced." />;
    return (
      <div className="flex flex-col gap-1.5">
        {territories.slice(0, 100).map((t) => (
          <button
            key={t.id}
            onClick={() => navigate(`/games/${gameId}/intel/territory/${t.id}`)}
            className="rounded border border-soot bg-void p-2 text-left hover:border-gold"
          >
            <div className="text-[11px] font-semibold text-bone">{t.name}</div>
            <div className="text-[9px] text-ash">
              county {t.county_fips ?? "?"} · pop {t.population} · HEAT {(t.heat * 100).toFixed(0)}%
            </div>
          </button>
        ))}
      </div>
    );
  }
  if (tab === "orgs") {
    if (orgs.length === 0) return <EmptyState label="No enemy orgs surfaced." />;
    return (
      <div className="flex flex-col gap-1.5">
        {orgs.map((o) => (
          <button
            key={o.id}
            onClick={() => navigate(`/games/${gameId}/intel/org/${o.id}`)}
            className="rounded border border-soot bg-void p-2 text-left hover:border-gold"
          >
            <div className="text-[11px] font-semibold text-bone">{o.short_name ?? o.name}</div>
            <div className="text-[9px] text-ash">
              {o.class_character} · OPC {((o.opacity ?? 0) * 100).toFixed(0)}%
            </div>
          </button>
        ))}
      </div>
    );
  }
  if (tab === "edges") {
    if (edges.length === 0) return <EmptyState label="No edges surfaced." />;
    return (
      <div className="flex flex-col gap-1.5">
        {edges.slice(0, 100).map((e) => (
          <button
            key={e.id}
            onClick={() => navigate(`/games/${gameId}/intel/edge/${e.id}`)}
            className="rounded border border-soot bg-void p-2 text-left hover:border-gold"
          >
            <div className="text-[11px] font-semibold text-bone">{e.mode}</div>
            <div className="text-[9px] text-ash">
              {e.source_id} → {e.target_id} · tension {(e.tension * 100).toFixed(0)}%
            </div>
          </button>
        ))}
      </div>
    );
  }
  if (communities.length === 0) return <EmptyState label="No communities surfaced." />;
  return (
    <div className="flex flex-col gap-1.5">
      {communities.slice(0, 100).map((c) => (
        <button
          key={c.id}
          onClick={() => navigate(`/games/${gameId}/intel/community/${c.id}`)}
          className="rounded border border-soot bg-void p-2 text-left hover:border-gold"
        >
          <div className="text-[11px] font-semibold text-bone">{c.label}</div>
          <div className="text-[9px] text-ash">
            {c.category} · {c.member_ids.length} member(s)
          </div>
        </button>
      ))}
    </div>
  );
}

interface DetailProps {
  targetType: string | undefined;
  targetId: string | undefined;
  territories: SnapshotTerritory[];
  orgs: OrgState[];
  edges: SnapshotEdge[];
  communities: HyperedgeState[];
}

function TerritoryDetail({ t }: { t: SnapshotTerritory }) {
  return (
    <div className="flex flex-col gap-3">
      <BblLabel color="#c8a860">{t.name}</BblLabel>
      <div className="flex gap-6">
        <Stat label="Heat" value={`${(t.heat * 100).toFixed(0)}%`} color="#e04040" />
        <Stat label="Rent" value={`${(t.rent_level * 100).toFixed(0)}%`} color="#a070d0" />
        <Stat label="Pop" value={String(t.population)} color="#80b0e0" />
        <Stat label="CON" value={`${((t.consciousness ?? 0) * 100).toFixed(0)}%`} color="#80b0e0" />
      </div>
      {t.dominant_community && (
        <div className="text-[10px] text-ash">
          Dominant community: <span className="text-bone">{t.dominant_community}</span>
        </div>
      )}
    </div>
  );
}

function OrgDetail({ o }: { o: OrgState }) {
  return (
    <div className="flex flex-col gap-3">
      <BblLabel color="#c8a860">{o.short_name ?? o.name}</BblLabel>
      <div className="flex gap-6">
        <Stat label="Cohesion" value={`${(o.cohesion * 100).toFixed(0)}%`} color="#c8a860" />
        <Stat label="Heat" value={`${(o.heat * 100).toFixed(0)}%`} color="#e04040" />
        <Stat label="Opacity" value={`${((o.opacity ?? 0) * 100).toFixed(0)}%`} color="#a070d0" />
      </div>
      <BblData size={10}>OODA phase: {o.ooda?.phase ?? "observe"}</BblData>
    </div>
  );
}

function EdgeDetail({ e }: { e: SnapshotEdge }) {
  const profit =
    e.rate_of_profit === null || e.rate_of_profit === undefined
      ? "n/a"
      : `${(e.rate_of_profit * 100).toFixed(0)}%`;
  const rent =
    e.rent_burden === null || e.rent_burden === undefined
      ? "n/a"
      : `${(e.rent_burden * 100).toFixed(0)}%`;
  return (
    <div className="flex flex-col gap-3">
      <BblLabel color="#c8a860">{e.mode}</BblLabel>
      <div className="text-[11px] text-ash">
        {e.source_id} → {e.target_id}
      </div>
      <div className="flex gap-6">
        <Stat label="Tension" value={`${(e.tension * 100).toFixed(0)}%`} color="#e04040" />
        <Stat label="Profit" value={profit} color="#a070d0" />
        <Stat label="Rent" value={rent} color="#80b0e0" />
      </div>
    </div>
  );
}

function CommunityDetail({ c }: { c: HyperedgeState }) {
  return (
    <div className="flex flex-col gap-3">
      <BblLabel color="#c8a860">{c.label}</BblLabel>
      <div className="flex items-center gap-2">
        <BblBadge color="#a070d0">{c.category}</BblBadge>
        <Stat
          label="Identity"
          value={`${(c.ideological_dimension.collective_identity_strength * 100).toFixed(0)}%`}
          color="#80b0e0"
        />
        <Stat label="Members" value={String(c.member_ids.length)} color="#c8a860" />
      </div>
      <div className="text-[10px] text-ash">{c.material_basis.description}</div>
      <div className="flex flex-wrap gap-1">
        {c.material_basis.indicators.map((indicator) => (
          <BblBadge key={indicator} color="#787878">
            {indicator}
          </BblBadge>
        ))}
      </div>
      <BblData size={10}>Members: {c.member_ids.join(", ")}</BblData>
    </div>
  );
}

function DetailPanel({ targetType, targetId, territories, orgs, edges, communities }: DetailProps) {
  if (!targetType || !targetId) return <EmptyState label="Pick a target from the index." />;
  if (targetType === "territory") {
    const t = territories.find((x) => x.id === targetId);
    return t ? <TerritoryDetail t={t} /> : <EmptyState label="Territory not found." />;
  }
  if (targetType === "org") {
    const o = orgs.find((x) => x.id === targetId);
    return o ? <OrgDetail o={o} /> : <EmptyState label="Org not found." />;
  }
  if (targetType === "edge") {
    const e = edges.find((x) => x.id === targetId);
    return e ? <EdgeDetail e={e} /> : <EmptyState label="Edge not found." />;
  }
  if (targetType === "community") {
    const c = communities.find((x) => x.id === targetId);
    return c ? <CommunityDetail c={c} /> : <EmptyState label="Community not found." />;
  }
  return <EmptyState label="Unknown target type." />;
}

export function IntelPageV2() {
  const {
    id: gameId,
    targetType,
    targetId,
  } = useParams<{ id: string; targetType: string; targetId: string }>();
  const navigate = useNavigate();
  const { snapshot } = useGameState(gameId ?? null);
  const [tab, setTab] = useState<IntelTab>("territories");

  const territories: SnapshotTerritory[] = useMemo(
    () => (snapshot?.territories ?? []) as unknown as SnapshotTerritory[],
    [snapshot],
  );
  const enemyOrgs: OrgState[] = useMemo(
    () => (snapshot?.organizations ?? []).filter((o) => !o.player_controlled),
    [snapshot],
  );
  const edges: SnapshotEdge[] = useMemo(
    () => (snapshot?.edges ?? []) as unknown as SnapshotEdge[],
    [snapshot],
  );
  const communities: HyperedgeState[] = useMemo(() => snapshot?.hyperedges ?? [], [snapshot]);

  const tabs: { key: IntelTab; label: string; count: number }[] = [
    { key: "territories", label: "Territories", count: territories.length },
    { key: "orgs", label: "Orgs", count: enemyOrgs.length },
    { key: "edges", label: "Edges", count: edges.length },
    { key: "communities", label: "Communities", count: communities.length },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Intel"
        subtitle="Surveillance index — territories, NPC orgs, edges, communities"
        breadcrumbs={["Operation", "Intel"]}
        right={<BblBadge color="#787878">read-only</BblBadge>}
      />

      <div className="grid min-h-0 flex-1 grid-cols-[360px_1fr] gap-3 p-3">
        <BblPanel
          title="Index"
          right={
            <div className="flex gap-1">
              {tabs.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`rounded border px-2 py-0.5 text-[9px] uppercase tracking-[0.15em] ${
                    tab === t.key
                      ? "border-gold bg-gold/15 text-gold"
                      : "border-wet-concrete text-ash"
                  }`}
                >
                  {t.label} {t.count}
                </button>
              ))}
            </div>
          }
        >
          <IndexList
            tab={tab}
            territories={territories}
            orgs={enemyOrgs}
            edges={edges}
            communities={communities}
            gameId={gameId}
            navigate={navigate}
          />
        </BblPanel>

        <BblPanel title="Detail" accent="#c8a860">
          <DetailPanel
            targetType={targetType}
            targetId={targetId}
            territories={territories}
            orgs={enemyOrgs}
            edges={edges}
            communities={communities}
          />
        </BblPanel>
      </div>
    </div>
  );
}
