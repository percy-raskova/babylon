/**
 * TerritoryDetailView — full territory drill-down (spec 093 US1).
 *
 * Ported from `design/mockups/ui_kits/webapp/TerritoryDetail.jsx`'s layout
 * onto live `GameSnapshot` data: the full material stat grid, the real
 * economic panel (`useEconomy`), organizations actually present in the
 * territory (derived from real `territory_ids`), and events actually
 * scoped to the territory. Every numeric stat in the material grid is
 * wrapped in `BreakdownTooltip` for provenance (FR-006/FR-009).
 *
 * Economy panel (FR-006 note): the 4 economy stats (value_produced,
 * rent_extracted, exploitation_rate, extraction_intensity) come from a
 * separate `/economy/` API call and have no `ScriptValue` selector
 * registered in the selectors registry — BreakdownTooltip requires a
 * selector for provenance drill-down. Wrapping them is deferred until
 * economy selectors are registered (follow-up spec).
 */

import { BblBadge, BblPanel, Stat } from "@/components/bbl";
import { BreakdownTooltip } from "@/components/inspector/BreakdownTooltip";
import { useEconomy } from "@/hooks/useEconomy";
import { selectors } from "@/lib/selectors";
import type { Scope } from "@/lib/selectors";
import type { GameSnapshot, OrgState, TerritoryState, GameEvent } from "@/types/game";

interface LooseTerritory extends TerritoryState {
  consciousness?: number;
  wealth?: number;
}

interface TerritoryDetailViewProps {
  territory: LooseTerritory;
  snapshot: GameSnapshot;
  gameId?: string;
}

function orgsInTerritory(snapshot: GameSnapshot, territoryId: string): OrgState[] {
  return snapshot.organizations.filter((o) => o.territory_ids.includes(territoryId));
}

/** Real (non-random) territory scoping: matches on any territory-shaped
 * reference the event's data payload carries. Events with no such
 * reference are honestly excluded rather than shown as if they belonged. */
function eventsForTerritory(snapshot: GameSnapshot, territory: LooseTerritory): GameEvent[] {
  const orgIdsHere = new Set(orgsInTerritory(snapshot, territory.id).map((o) => o.id));
  return snapshot.events.filter((e) => {
    const data = e.data as Record<string, unknown>;
    if (data.territory_id === territory.id) return true;
    if (data.county_fips && data.county_fips === territory.county_fips) return true;
    const orgId = data.org_id ?? data.source_id ?? data.target_id;
    return typeof orgId === "string" && orgIdsHere.has(orgId);
  });
}

function StatWithBreakdown({
  selectorName,
  scope,
  value,
  format,
  color,
}: {
  selectorName: string;
  scope: Scope;
  value: string;
  format?: (v: number) => string;
  color: string;
}) {
  const selector = selectors.get(selectorName);
  return (
    <BreakdownTooltip selector={selector} scope={scope} format={format}>
      <Stat label={selector.label} value={value} color={color} wrap={false} />
    </BreakdownTooltip>
  );
}

export function TerritoryDetailView({ territory, snapshot }: TerritoryDetailViewProps) {
  const scope: Scope = { snapshot, this: { kind: "hex", id: territory.id } };
  const economy = useEconomy(snapshot.session_id, territory.id);
  const orgs = orgsInTerritory(snapshot, territory.id);
  const events = eventsForTerritory(snapshot, territory);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline gap-3">
        <h2 className="text-xl font-bold text-bone">{territory.name}</h2>
        <BblBadge color="#787878">{territory.territory_type}</BblBadge>
        <span className="ml-auto text-[10px] text-ash">
          county {territory.county_fips} · pop {territory.population.toLocaleString()}
        </span>
      </div>

      <div className="grid grid-cols-6 gap-2">
        <StatWithBreakdown
          selectorName="hex.heat"
          scope={scope}
          value={`${(territory.heat * 100).toFixed(0)}%`}
          color="#e04040"
        />
        <StatWithBreakdown
          selectorName="hex.rent_level"
          scope={scope}
          value={territory.rent_level.toFixed(2)}
          color="#a070d0"
        />
        <StatWithBreakdown
          selectorName="hex.consciousness"
          scope={scope}
          value={`${((territory.consciousness ?? 0) * 100).toFixed(0)}%`}
          color="#80b0e0"
        />
        <StatWithBreakdown
          selectorName="hex.wealth"
          scope={scope}
          value={(territory.wealth ?? 0).toFixed(1)}
          color="#c8a860"
        />
        <StatWithBreakdown
          selectorName="hex.biocapacity"
          scope={scope}
          value={territory.biocapacity.toFixed(2)}
          color="#5fbf7a"
        />
        <StatWithBreakdown
          selectorName="hex.population"
          scope={scope}
          value={territory.population.toLocaleString()}
          color="#7a6db8"
        />
      </div>
      {territory.under_eviction && <BblBadge color="#e04040">Under Eviction</BblBadge>}

      <BblPanel title="Economy" accent="#c8a860">
        {!economy.data.has_data ? (
          <div className="text-[11px] text-ash">No economic data yet for this territory.</div>
        ) : (
          <div className="grid grid-cols-4 gap-3">
            <Stat
              label="Value Produced"
              value={economy.data.value_produced.toFixed(1)}
              color="#c8a860"
            />
            <Stat
              label="Rent Extracted"
              value={economy.data.rent_extracted.toFixed(1)}
              color="#a070d0"
            />
            <Stat
              label="Exploitation Rate"
              value={
                economy.data.exploitation_rate === null
                  ? "n/a"
                  : `${(economy.data.exploitation_rate * 100).toFixed(0)}%`
              }
              color="#e04040"
            />
            <Stat
              label="Extraction Intensity"
              value={economy.data.extraction_intensity.toFixed(2)}
              color="#80b0e0"
            />
          </div>
        )}
      </BblPanel>

      <div className="grid grid-cols-2 gap-3">
        <BblPanel title="Active Organizations" accent="#2a2a3a">
          {orgs.length === 0 ? (
            <div className="text-[11px] text-ash">No organizations present.</div>
          ) : (
            <div className="flex flex-col gap-2">
              {orgs.map((o) => (
                <div key={o.id} className="flex items-center justify-between text-[12px]">
                  <span className="text-bone">{o.short_name ?? o.name}</span>
                  <BblBadge color={o.player_controlled ? "#5fbf7a" : "#787878"}>
                    {o.player_controlled ? "own" : o.class_character}
                  </BblBadge>
                </div>
              ))}
            </div>
          )}
        </BblPanel>

        <BblPanel title="Recent Events" accent="#2a2a3a">
          {events.length === 0 ? (
            <div className="text-[11px] text-ash">No events scoped to this territory yet.</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {events.slice(0, 6).map((e) => (
                <div key={e.id} className="flex gap-2 text-[11px]">
                  <span className="text-shroud">t={e.tick}</span>
                  <span className="text-ash">{e.title}</span>
                </div>
              ))}
            </div>
          )}
        </BblPanel>
      </div>
    </div>
  );
}
