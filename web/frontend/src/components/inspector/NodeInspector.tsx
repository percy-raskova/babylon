/**
 * Node inspector — shows detailed attributes for an entity, organization,
 * or institution selected in the graph or map.
 */

import type { EntityState, OrgState, InstitutionState, GameSnapshot } from "@/types/game";

interface NodeInspectorProps {
  snapshot: GameSnapshot;
  nodeId: string;
}

export function NodeInspector({ snapshot, nodeId }: NodeInspectorProps) {
  const entity = snapshot.entities.find((e) => e.id === nodeId);
  if (entity) return <EntityDetail entity={entity} />;

  const org = snapshot.organizations.find((o) => o.id === nodeId);
  if (org) return <OrgDetail org={org} />;

  const inst = snapshot.institutions.find((i) => i.id === nodeId);
  if (inst) return <InstitutionDetail inst={inst} />;

  return <p className="text-sm text-ash">Unknown node: {nodeId}</p>;
}

/** Stat row with label/value pair. */
function Stat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  const display = typeof value === "number" ? value.toFixed(2) : value;
  return (
    <div className="flex justify-between py-0.5 text-[12px]">
      <span className="text-ash">{label}</span>
      <span className={`font-mono font-semibold ${color ?? "text-bone"}`}>{display}</span>
    </div>
  );
}

/** Bar gauge for [0,1] probability-like values. */
function Bar({ value, color }: { value: number; color: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
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

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    proletariat: "bg-crimson/20 text-crimson",
    bourgeoisie: "bg-gold/20 text-gold",
    lumpenproletariat: "bg-phosphor-red/20 text-phosphor-red",
    petty_bourgeoisie: "bg-royal-blue/20 text-royal-blue",
    labor_aristocracy: "bg-silver/20 text-silver",
  };
  const cls = colors[role.toLowerCase()] ?? "bg-soot text-ash";
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${cls}`}
    >
      {role}
    </span>
  );
}

function EntityDetail({ entity }: { entity: EntityState }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-royal-blue">{entity.name}</span>
        <RoleBadge role={entity.role} />
      </div>

      <SectionHeader label="Survival" />
      <Stat label="P(Acquiescence)" value={entity.p_acquiescence} color="text-data-green" />
      <Bar value={entity.p_acquiescence} color="#4ade80" />
      <Stat label="P(Revolution)" value={entity.p_revolution} color="text-phosphor-red" />
      <Bar value={entity.p_revolution} color="#e63946" />

      <SectionHeader label="Economics" />
      <Stat label="Wealth" value={entity.wealth} color="text-data-green" />
      <Stat label="Subsistence" value={entity.subsistence} />
      <Stat label="Population" value={entity.population} />
      <Stat label="Inequality (Gini)" value={entity.inequality} />

      <SectionHeader label="Consciousness" />
      <Stat label="Consciousness" value={entity.consciousness} color="text-gold" />
      <Bar value={entity.consciousness} color="#d4a843" />
      <Stat label="Organization" value={entity.organization} color="text-royal-blue" />
      <Bar value={entity.organization} color="#6a9fdb" />
      <Stat label="Agitation" value={entity.agitation} />
      <Stat label="National Identity" value={entity.national_identity} />
      <Stat label="Repression" value={entity.repression} color="text-crimson" />
    </div>
  );
}

function OrgDetail({ org }: { org: OrgState }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-grow-purple">{org.name}</span>
        <span className="rounded bg-grow-purple/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-grow-purple">
          {org.org_type}
        </span>
      </div>

      <SectionHeader label="Identity" />
      <Stat label="Class Character" value={org.class_character} />
      <Stat label="Consciousness" value={org.consciousness_tendency} />

      <SectionHeader label="Capacity" />
      <Stat label="Budget" value={org.budget} color="text-data-green" />
      <Stat label="Cohesion" value={org.cohesion} color="text-gold" />
      <Bar value={org.cohesion} color="#d4a843" />
      <Stat label="Cadre Level" value={org.cadre_level} color="text-royal-blue" />
      <Stat label="Heat" value={org.heat} color="text-crimson" />
      <Bar value={org.heat} color="#e63946" />

      {org.territory_ids.length > 0 && (
        <>
          <SectionHeader label="Territories" />
          <div className="flex flex-wrap gap-1">
            {org.territory_ids.map((tid) => (
              <span
                key={tid}
                className="rounded bg-soot px-1.5 py-0.5 text-[10px] font-mono text-ash"
              >
                {tid}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function InstitutionDetail({ inst }: { inst: InstitutionState }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-silver">{inst.name}</span>
        <span className="rounded bg-silver/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-silver">
          {inst.apparatus_type}
        </span>
      </div>

      <SectionHeader label="Character" />
      <Stat label="Social Function" value={inst.social_function} />
      <Stat label="Class Inscription" value={inst.class_inscription} />
      <Stat label="Hegemonic Fraction" value={inst.hegemonic_fraction} />

      <SectionHeader label="Resources" />
      <Stat label="Legitimacy" value={inst.legitimacy} color="text-gold" />
      <Bar value={inst.legitimacy} color="#d4a843" />
      <Stat label="Budget" value={inst.budget} color="text-data-green" />

      <SectionHeader label="Internal Balance" />
      <Stat
        label="Liberal-Technocratic"
        value={inst.liberal_technocratic}
        color="text-royal-blue"
      />
      <Bar value={inst.liberal_technocratic} color="#6a9fdb" />
      <Stat label="Revanchist-Fascist" value={inst.revanchist_fascist} color="text-crimson" />
      <Bar value={inst.revanchist_fascist} color="#e63946" />
      <Stat
        label="Institutionalist-Bonapartist"
        value={inst.institutionalist_bonapartist}
        color="text-gold"
      />
      <Bar value={inst.institutionalist_bonapartist} color="#d4a843" />

      {inst.housed_org_ids.length > 0 && (
        <>
          <SectionHeader label="Housed Organizations" />
          <div className="flex flex-wrap gap-1">
            {inst.housed_org_ids.map((oid) => (
              <span
                key={oid}
                className="rounded bg-grow-purple/20 px-1.5 py-0.5 text-[10px] font-mono text-grow-purple"
              >
                {oid}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
