/**
 * Stat preview — one label/value row with null-honesty (`null` renders as
 * "no data"). Pure props. Curated as the stacked compositions its only
 * callers (InspectorPanel's OrgFields/TerritoryFields) actually use, rather
 * than isolated single rows.
 */
import { Stat } from "babylon-cockpit";

// Inline style for width: .design-sync/previews/ isn't in Tailwind's
// content-scan root, so w-[280px] never compiles (see learnings).
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="flex flex-col gap-1 bg-void p-3" style={{ width: 280 }}>
      {children as never}
    </div>
  );
}

export function OrgStatsPopulated() {
  return (
    <Frame>
      <Stat label="Class Character" value="proletarian" />
      <Stat label="Budget" value={84.2} />
      <Stat label="Cohesion" value={0.58} />
      <Stat label="Heat" value={0.34} />
    </Frame>
  );
}

export function TerritoryStatsPopulated() {
  return (
    <Frame>
      <Stat label="Habitability" value={0.24} />
      <Stat label="Biocapacity" value={0.18} />
      <Stat label="Heat" value={0.71} />
      <Stat label="Rent Level" value={0.62} />
      <Stat label="Population" value={84213} />
    </Frame>
  );
}

export function AllNoData() {
  return (
    <Frame>
      <Stat label="Habitability" value={null} />
      <Stat label="Biocapacity" value={null} />
      <Stat label="Heat" value={null} />
    </Frame>
  );
}
