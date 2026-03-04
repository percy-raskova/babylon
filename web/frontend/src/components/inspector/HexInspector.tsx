/**
 * Hex inspector — shows detailed territory attributes for a selected hex.
 * Clickable org rows for drill-down into organization detail.
 */

import { useUIStore } from "@/stores/uiStore";
import type { TerritoryState, GameSnapshot } from "@/types/game";

interface HexInspectorProps {
  snapshot: GameSnapshot;
  hexId: string;
}

export function HexInspector({ snapshot, hexId }: HexInspectorProps) {
  const territory = snapshot.territories.find((t) => t.id === hexId);
  if (!territory) {
    return <p className="text-sm text-ash">Unknown territory: {hexId}</p>;
  }

  return <TerritoryDetail territory={territory} snapshot={snapshot} />;
}

function Stat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  const display = typeof value === "number" ? value.toFixed(2) : value;
  return (
    <div className="flex justify-between py-0.5 text-[12px]">
      <span className="text-ash">{label}</span>
      <span className={`font-mono font-semibold ${color ?? "text-bone"}`}>{display}</span>
    </div>
  );
}

function Bar({ value, color, max = 1 }: { value: number; color: string; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="h-1.5 w-full rounded-full bg-soot">
      <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  );
}

function SectionHeader({ label }: { label: string }) {
  return (
    <h4 className="mb-1 mt-3 border-b border-soot pb-1 text-[10px] uppercase tracking-widest text-ash first:mt-0">
      {label}
    </h4>
  );
}

function ProfileBadge({ profile }: { profile: string }) {
  const colors: Record<string, string> = {
    HIGH_PROFILE: "bg-crimson/20 text-crimson",
    LOW_PROFILE: "bg-data-green/20 text-data-green",
    NEUTRAL: "bg-soot text-ash",
  };
  const cls = colors[profile] ?? "bg-soot text-ash";
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${cls}`}
    >
      {profile}
    </span>
  );
}

function TerritoryDetail({
  territory,
  snapshot,
}: {
  territory: TerritoryState;
  snapshot: GameSnapshot;
}) {
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);
  const host = territory.host_id ? snapshot.entities.find((e) => e.id === territory.host_id) : null;
  const occupant = territory.occupant_id
    ? snapshot.entities.find((e) => e.id === territory.occupant_id)
    : null;

  // Find orgs present in this territory
  const presentOrgs = snapshot.organizations.filter((o) => o.territory_ids.includes(territory.id));

  // Find edges connected to this territory
  const connectedEdges = snapshot.edges.filter(
    (e) => e.source_id === territory.id || e.target_id === territory.id,
  );

  // Recent events affecting this territory
  const territoryEvents = snapshot.events
    .filter((e) => e.data.territory_id === territory.id)
    .slice(-5);

  return (
    <div className="flex flex-col gap-0.5">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-gold">{territory.name}</span>
        <ProfileBadge profile={territory.profile} />
      </div>

      <SectionHeader label="Classification" />
      <Stat label="Sector" value={territory.sector_type} />
      <Stat label="Type" value={territory.territory_type} />
      {territory.h3_index && <Stat label="H3 Index" value={territory.h3_index} />}

      <SectionHeader label="Dynamics" />
      <Stat label="Heat" value={territory.heat} color="text-crimson" />
      <Bar value={territory.heat} color="#e63946" />
      <Stat label="Rent Level" value={territory.rent_level} color="text-gold" />
      <Stat label="Population" value={territory.population} />
      <Stat label="Biocapacity" value={territory.biocapacity} color="text-data-green" />
      <Bar value={territory.biocapacity} color="#4ade80" />

      {territory.under_eviction && (
        <div className="mt-1 rounded border border-crimson/30 bg-crimson/10 px-2 py-1 text-[11px] font-semibold text-crimson">
          UNDER EVICTION
        </div>
      )}

      {(host || occupant) && (
        <>
          <SectionHeader label="Occupants" />
          {host && (
            <button
              onClick={() => setSelectedNode(host.id)}
              className="flex w-full justify-between py-0.5 text-[12px] text-left transition-colors hover:text-gold"
            >
              <span className="text-ash">Host</span>
              <span className="font-mono font-semibold text-royal-blue">{host.name}</span>
            </button>
          )}
          {occupant && (
            <button
              onClick={() => setSelectedNode(occupant.id)}
              className="flex w-full justify-between py-0.5 text-[12px] text-left transition-colors hover:text-gold"
            >
              <span className="text-ash">Occupant</span>
              <span className="font-mono font-semibold text-royal-blue">{occupant.name}</span>
            </button>
          )}
        </>
      )}

      {presentOrgs.length > 0 && (
        <>
          <SectionHeader label={`Organizations (${presentOrgs.length})`} />
          <div className="flex flex-col gap-0.5">
            {presentOrgs.map((org) => (
              <button
                key={org.id}
                onClick={() => setSelectedNode(org.id)}
                className="flex w-full items-center justify-between rounded px-1 py-1 text-[11px] text-left transition-colors hover:bg-soot/50"
              >
                <span className="font-semibold text-grow-purple">{org.name}</span>
                <span className="rounded bg-soot px-1.5 py-0.5 text-[9px] text-ash">
                  {org.org_type}
                </span>
              </button>
            ))}
          </div>
        </>
      )}

      {territoryEvents.length > 0 && (
        <>
          <SectionHeader label="Recent Events" />
          <div className="flex flex-col gap-0.5">
            {territoryEvents.map((evt, i) => (
              <div
                key={`${evt.tick}-${evt.type}-${i}`}
                className="flex items-center justify-between text-[10px]"
              >
                <span className="text-ash">T{evt.tick}</span>
                <span className="font-semibold text-gold">{evt.type}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {connectedEdges.length > 0 && (
        <>
          <SectionHeader label={`Edges (${connectedEdges.length})`} />
          <div className="flex flex-col gap-1">
            {connectedEdges.slice(0, 10).map((edge, i) => (
              <div
                key={`${edge.source_id}-${edge.target_id}-${edge.edge_type}-${i}`}
                className="flex items-center justify-between text-[11px]"
              >
                <span className="text-ash">{edge.edge_type}</span>
                <span className="font-mono text-bone">{edge.value_flow.toFixed(1)}</span>
              </div>
            ))}
            {connectedEdges.length > 10 && (
              <span className="text-[10px] text-ash">+{connectedEdges.length - 10} more</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
