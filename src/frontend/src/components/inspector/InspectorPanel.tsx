/**
 * Inspector — Right Dock tab 2. Selected node/edge/org/community/hex
 * detail, sourced from `panels.inspector` (fanned out by
 * `mapSlice.setSelection`). Enemy orgs are allowed here — unlike the
 * Action Composer's acting-org selector, inspecting is read-only and has
 * no "act as the enemy" concern.
 */

import { useStore } from "@/store";
import { readNumberField, readStringField, readConsciousness } from "@/lib/inspectorFields";
import { Stat } from "./Stat";
import { ConsciousnessBreakdown } from "./ConsciousnessBreakdown";

export function InspectorPanel(): React.JSX.Element {
  const selection = useStore((s) => s.map.selection);
  const data = useStore((s) => s.panels.inspector.data);
  const loading = useStore((s) => s.panels.inspector.loading);
  const error = useStore((s) => s.panels.inspector.error);

  if (!selection) {
    return (
      <p className="p-3 text-[11px] italic text-shroud" data-testid="inspector-empty">
        Select a node, edge, org, community, or hex to inspect.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2 p-2" data-testid="inspector-panel">
      <div className="flex items-baseline justify-between border-b border-rebar pb-1.5">
        <span className="font-mono text-[11px] font-semibold text-spire">{selection.id}</span>
        <span className="text-[9px] uppercase tracking-widest text-ash">{selection.kind}</span>
      </div>

      {loading && <p className="text-[11px] text-ash">Loading…</p>}
      {error && (
        <p role="alert" className="text-[11px] text-laser">
          {error}
        </p>
      )}
      {!loading && !error && data === null && (
        <p className="text-[11px] italic text-shroud">No data returned for this selection.</p>
      )}
      {!loading && !error && data !== null && <InspectorFields kind={selection.kind} data={data} />}
    </div>
  );
}

interface InspectorFieldsProps {
  kind: string;
  data: Record<string, unknown>;
}

function InspectorFields({ kind, data }: InspectorFieldsProps): React.JSX.Element {
  if (kind === "org") return <OrgFields data={data} />;
  if (kind === "hex") return <TerritoryFields data={data} />;
  return <GenericFields data={data} />;
}

function OrgFields({ data }: { data: Record<string, unknown> }): React.JSX.Element {
  const consciousness = readConsciousness(data);
  return (
    <div className="flex flex-col gap-1">
      <Stat label="Class Character" value={readStringField(data, "class_character")} />
      <Stat label="Budget" value={readNumberField(data, "budget")} />
      <Stat label="Cohesion" value={readNumberField(data, "cohesion")} />
      <Stat label="Heat" value={readNumberField(data, "heat")} />
      <ConsciousnessBreakdown consciousness={consciousness} />
    </div>
  );
}

function TerritoryFields({ data }: { data: Record<string, unknown> }): React.JSX.Element {
  return (
    <div className="flex flex-col gap-1">
      <Stat label="Habitability" value={readNumberField(data, "habitability")} />
      <Stat label="Biocapacity" value={readNumberField(data, "biocapacity")} />
      <Stat label="Heat" value={readNumberField(data, "heat")} />
      <Stat label="Rent Level" value={readNumberField(data, "rent_level")} />
      <Stat label="Population" value={readNumberField(data, "population")} />
    </div>
  );
}

function GenericFields({ data }: { data: Record<string, unknown> }): React.JSX.Element {
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return <p className="text-[11px] italic text-shroud">Empty detail payload.</p>;
  }
  return (
    <div className="flex flex-col gap-0.5">
      {entries.map(([key, value]) => (
        <div key={key} className="flex justify-between gap-2 text-[11px]">
          <span className="text-ash">{key}</span>
          <span className="truncate font-mono text-bone">{JSON.stringify(value)}</span>
        </div>
      ))}
    </div>
  );
}
