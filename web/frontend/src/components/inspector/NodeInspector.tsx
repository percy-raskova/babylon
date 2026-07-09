/**
 * Node inspector — shows detailed attributes for an organization
 * or institution selected in the graph or map.
 * Clickable territory rows for drill-down into territory detail.
 *
 * Note: Entity detail view is removed (Spec 052 — classes are derived,
 * not graph nodes).
 */

import { useUIStore } from "@/stores/uiStore";
import type { OrgState, InstitutionState, GameSnapshot } from "@/types/game";

interface NodeInspectorProps {
  snapshot: GameSnapshot;
  nodeId: string;
}

export function NodeInspector({ snapshot, nodeId }: NodeInspectorProps) {
  const org = snapshot.organizations.find((o) => o.id === nodeId);
  if (org) return <OrgDetail org={org} snapshot={snapshot} />;

  const inst = snapshot.institutions.find((i) => i.id === nodeId);
  if (inst) return <InstitutionDetail inst={inst} snapshot={snapshot} />;

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

function OrgDetail({ org, snapshot }: { org: OrgState; snapshot: GameSnapshot }) {
  const setSelectedHex = useUIStore((s) => s.setSelectedHex);
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);

  // Resolve territory names from IDs
  const territories = org.territory_ids
    .map((tid) => snapshot.territories.find((t) => t.id === tid))
    .filter((t): t is NonNullable<typeof t> => t !== undefined);

  // Find hyperedge memberships
  const hyperedges = (org.hyperedge_memberships ?? [])
    .map((hid) => snapshot.hyperedges.find((hx) => hx.id === hid))
    .filter((hx): hx is NonNullable<typeof hx> => hx !== undefined);

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

      <SectionHeader label="Consciousness" />
      {org.consciousness ? (
        <>
          <Stat
            label="Revolutionary"
            value={org.consciousness.revolutionary}
            color="text-crimson"
          />
          <Bar value={org.consciousness.revolutionary} color="#e63946" />
          <Stat label="Liberal" value={org.consciousness.liberal} color="text-royal-blue" />
          <Bar value={org.consciousness.liberal} color="#6a9fdb" />
          <Stat label="Fascist" value={org.consciousness.fascist} color="text-gold" />
          <Bar value={org.consciousness.fascist} color="#d4a843" />
        </>
      ) : (
        <Stat label="Distribution" value="no data" />
      )}

      <SectionHeader label="Capacity" />
      <Stat label="Budget" value={org.budget} color="text-data-green" />
      <Stat label="Cohesion" value={org.cohesion} color="text-gold" />
      <Bar value={org.cohesion} color="#d4a843" />
      <Stat label="Cadre Level" value={org.cadre_level} color="text-royal-blue" />
      <Stat label="Heat" value={org.heat} color="text-crimson" />
      <Bar value={org.heat} color="#e63946" />

      <SectionHeader label="OODA Loop" />
      <Stat label="Observe" value={org.ooda.observe} />
      <Stat label="Orient" value={org.ooda.orient} />
      <Stat label="Decide" value={org.ooda.decide} />
      <Stat label="Act" value={org.ooda.act} />
      <Stat label="Cycle Ticks" value={org.ooda.cycle_ticks} />

      {territories.length > 0 && (
        <>
          <SectionHeader label={`Territories (${territories.length})`} />
          <div className="flex flex-col gap-0.5">
            {territories.map((terr) => (
              <button
                key={terr.id}
                onClick={() => {
                  setSelectedNode(null);
                  setSelectedHex(terr.id);
                }}
                className="flex w-full items-center justify-between rounded px-1 py-1 text-[11px] text-left transition-colors hover:bg-soot/50"
              >
                <span className="font-semibold text-gold">{terr.name}</span>
                <span className="font-mono text-ash">{terr.heat.toFixed(2)} heat</span>
              </button>
            ))}
          </div>
        </>
      )}

      {hyperedges.length > 0 && (
        <>
          <SectionHeader label={`Communities (${hyperedges.length})`} />
          <div className="flex flex-col gap-0.5">
            {hyperedges.map((hx) => (
              <div
                key={hx.id}
                className="flex w-full items-center justify-between rounded px-1 py-1 text-[11px]"
              >
                <span className="font-semibold text-royal-blue">{hx.label}</span>
                <span className="rounded bg-soot px-1.5 py-0.5 text-[9px] text-ash">
                  {hx.category}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function InstitutionDetail({ inst, snapshot }: { inst: InstitutionState; snapshot: GameSnapshot }) {
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);

  // Resolve housed org names
  const housedOrgs = inst.housed_org_ids
    .map((oid) => snapshot.organizations.find((o) => o.id === oid))
    .filter((o): o is NonNullable<typeof o> => o !== undefined);

  const fc = inst.factional_composition;

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

      <SectionHeader label="Resources" />
      <Stat label="Legitimacy" value={inst.legitimacy} color="text-gold" />
      <Bar value={inst.legitimacy} color="#d4a843" />
      <Stat label="Budget" value={inst.budget} color="text-data-green" />

      <SectionHeader label="Internal Balance" />
      <Stat label="Liberal-Technocratic" value={fc.liberal_technocratic} color="text-royal-blue" />
      <Bar value={fc.liberal_technocratic} color="#6a9fdb" />
      <Stat label="Revanchist-Fascist" value={fc.revanchist_fascist} color="text-crimson" />
      <Bar value={fc.revanchist_fascist} color="#e63946" />
      <Stat
        label="Institutionalist-Bonapartist"
        value={fc.institutionalist_bonapartist}
        color="text-gold"
      />
      <Bar value={fc.institutionalist_bonapartist} color="#d4a843" />

      {housedOrgs.length > 0 && (
        <>
          <SectionHeader label={`Housed Organizations (${housedOrgs.length})`} />
          <div className="flex flex-col gap-0.5">
            {housedOrgs.map((org) => (
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
    </div>
  );
}
