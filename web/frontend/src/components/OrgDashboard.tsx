/**
 * Organization dashboard component.
 *
 * Displays organization state: resources, type, class character,
 * and key metrics for each org in the game.
 */

import { useState } from "react";
import type { GameSnapshot } from "@/types/game";

interface OrgDashboardProps {
  snapshot: GameSnapshot;
  onSelectOrg?: (orgId: string) => void;
}

export function OrgDashboard({ snapshot, onSelectOrg }: OrgDashboardProps) {
  const [selectedOrg, setSelectedOrg] = useState<string | null>(null);

  const orgs = snapshot.organizations;

  function handleSelect(orgId: string) {
    setSelectedOrg(orgId === selectedOrg ? null : orgId);
    onSelectOrg?.(orgId);
  }

  return (
    <div className="flex h-full flex-col">
      <h3 className="mb-3 shrink-0 text-sm font-semibold uppercase tracking-wider text-gold">
        Organizations
      </h3>

      {orgs.length === 0 ? (
        <p className="text-center text-sm text-ash">No organizations in this game</p>
      ) : (
        <div className="flex flex-1 flex-col gap-2 overflow-auto">
          {orgs.map((org) => (
            <button
              key={org.id}
              onClick={() => handleSelect(org.id)}
              className={`w-full rounded-md border bg-void px-3.5 py-2.5 text-left text-[13px] text-bone ${
                selectedOrg === org.id ? "border-gold" : "border-wet-concrete hover:border-silver"
              }`}
            >
              <div className="mb-1.5 flex justify-between">
                <span className="font-semibold text-royal-blue">{org.name}</span>
                <span className="text-[11px] uppercase tracking-wider text-ash">
                  {org.org_type}
                </span>
              </div>
              <div className="flex gap-4">
                <OrgStat label="Budget" value={org.budget} />
                <OrgStat label="Class" value={org.class_character} />
                <OrgStat label="Cohesion" value={org.cohesion} />
              </div>
              {selectedOrg === org.id && (
                <pre className="mt-2 break-all whitespace-pre-wrap rounded bg-[#0a0a14] p-2 text-[11px] text-ash">
                  {JSON.stringify(org, null, 2)}
                </pre>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function OrgStat({ label, value }: { label: string; value: number | string }) {
  const display = typeof value === "number" ? value.toFixed(1) : value;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-ash">{label}</span>
      <span className="font-mono text-sm font-semibold text-bone">{display}</span>
    </div>
  );
}
