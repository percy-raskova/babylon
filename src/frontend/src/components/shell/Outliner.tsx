/**
 * Left Outliner — collapsible orgs / communities / factions lists.
 * Clicking a row drives the Inspector + map highlight via
 * `map.setSelection`. Factions read off `panels.map`'s balkanization
 * block; `MapPanel` owns that panel's mount/fetch lifecycle (both it and
 * this component are always mounted together for AppShell's lifetime, so
 * there is exactly one owner — see `panelFactory.ts`'s docstring on the
 * boolean (not refcounted) `mounted` flag).
 *
 * Filter box + compact-density toggle (Design Bible §5.1, shipped at
 * launch rather than retrofitted per the Paradox lesson that list
 * surfaces degrade as the player accumulates orgs/communities). Both are
 * local view state — they never touch the store, so they reset on
 * remount by design (nothing here is worth persisting across sessions
 * yet; promote to `uiSlice` later if that changes).
 */

import { useEffect, useState } from "react";
import { useStore } from "@/store";
import { factionsFromMapData } from "@/lib/mapMetadata";
import type { FactionSummary } from "@/components/map/mapLensLayers";
import type { CommunityEntry, OrgState } from "@/types/game";
import type { Selection } from "@/store/slices/mapSlice";
import { OutlinerSection } from "./OutlinerSection";
import { OutlinerRow } from "./OutlinerRow";

interface OutlinerProps {
  gameId: string;
}

function matchesFilter(query: string, label: string, sublabel?: string): boolean {
  if (!query) return true;
  return label.toLowerCase().includes(query) || (sublabel?.toLowerCase().includes(query) ?? false);
}

interface OrganizationsSectionProps {
  orgs: OrgState[];
  filtered: OrgState[];
  filterText: string;
  compact: boolean;
  selection: Selection | null;
  setSelection: (s: Selection) => void;
}

function OrganizationsSection({
  orgs,
  filtered,
  filterText,
  compact,
  selection,
  setSelection,
}: OrganizationsSectionProps): React.JSX.Element {
  return (
    <OutlinerSection title="Organizations" count={filtered.length} compact={compact}>
      {orgs.length === 0 && <EmptyRow text="No organizations in this session." />}
      {orgs.length > 0 && filtered.length === 0 && (
        <EmptyRow text={`No organizations match "${filterText}".`} />
      )}
      {filtered.map((org) => (
        <OutlinerRow
          key={org.id}
          label={org.short_name ?? org.name}
          sublabel={org.org_type}
          compact={compact}
          selected={selection?.kind === "org" && selection.id === org.id}
          onClick={() => setSelection({ kind: "org", id: org.id })}
        />
      ))}
    </OutlinerSection>
  );
}

interface CommunitiesSectionProps {
  loaded: boolean;
  communities: CommunityEntry[];
  filtered: CommunityEntry[];
  filterText: string;
  compact: boolean;
  selection: Selection | null;
  setSelection: (s: Selection) => void;
}

function CommunitiesSection({
  loaded,
  communities,
  filtered,
  filterText,
  compact,
  selection,
  setSelection,
}: CommunitiesSectionProps): React.JSX.Element {
  return (
    <OutlinerSection title="Communities" count={filtered.length} compact={compact}>
      {!loaded && <EmptyRow text="Communities not loaded yet." />}
      {loaded && communities.length === 0 && <EmptyRow text="No communities formed yet." />}
      {loaded && communities.length > 0 && filtered.length === 0 && (
        <EmptyRow text={`No communities match "${filterText}".`} />
      )}
      {filtered.map((c) => (
        <OutlinerRow
          key={c.id}
          label={c.dominant_role ?? c.id}
          sublabel={`${c.member_count} members`}
          compact={compact}
          selected={selection?.kind === "community" && selection.id === c.id}
          onClick={() => setSelection({ kind: "community", id: c.id })}
        />
      ))}
    </OutlinerSection>
  );
}

interface FactionsSectionProps {
  factions: FactionSummary[];
  filtered: FactionSummary[];
  filterText: string;
  compact: boolean;
  factionFilter: string | null;
  selectFaction: (id: string) => void;
}

function FactionsSection({
  factions,
  filtered,
  filterText,
  compact,
  factionFilter,
  selectFaction,
}: FactionsSectionProps): React.JSX.Element {
  return (
    <OutlinerSection title="Factions" count={filtered.length} compact={compact}>
      {factions.length === 0 && <EmptyRow text="No faction data — collapse layer unseeded." />}
      {factions.length > 0 && filtered.length === 0 && (
        <EmptyRow text={`No factions match "${filterText}".`} />
      )}
      {filtered.map((f) => (
        <OutlinerRow
          key={f.id}
          label={f.id}
          sublabel={f.colonial_stance}
          compact={compact}
          selected={factionFilter === f.id}
          onClick={() => selectFaction(f.id)}
        />
      ))}
    </OutlinerSection>
  );
}

export function Outliner({ gameId }: OutlinerProps): React.JSX.Element {
  const snapshot = useStore((s) => s.world.snapshot);
  const orgs = snapshot?.organizations ?? [];
  const communitiesData = useStore((s) => s.panels.communities.data);
  const fetchCommunities = useStore((s) => s.panels.communities.fetch);
  const setCommunitiesMounted = useStore((s) => s.panels.communities.setMounted);
  const mapData = useStore((s) => s.panels.map.data);
  const selection = useStore((s) => s.map.selection);
  const setSelection = useStore((s) => s.map.setSelection);
  const factionFilter = useStore((s) => s.map.factionFilter);
  const setFactionFilter = useStore((s) => s.map.setFactionFilter);
  const setLens = useStore((s) => s.map.setLens);

  const [filterText, setFilterText] = useState("");
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    setCommunitiesMounted(true);
    void fetchCommunities(gameId);
    return () => setCommunitiesMounted(false);
  }, [gameId, fetchCommunities, setCommunitiesMounted]);

  const communities = communitiesData?.communities ?? [];
  const factions = factionsFromMapData(mapData);

  const query = filterText.trim().toLowerCase();
  const filteredOrgs = orgs.filter((org) =>
    matchesFilter(query, org.short_name ?? org.name, org.org_type),
  );
  const filteredCommunities = communities.filter((c) =>
    matchesFilter(query, c.dominant_role ?? c.id, `${c.member_count} members`),
  );
  const filteredFactions = factions.filter((f) => matchesFilter(query, f.id, f.colonial_stance));

  function selectFaction(id: string): void {
    setFactionFilter(factionFilter === id ? null : id);
    setLens({ kind: "faction" });
  }

  return (
    <nav
      data-testid="region-outliner"
      aria-label="Outliner"
      className="row-start-2 flex flex-col gap-3 overflow-y-auto border-r border-rebar p-2"
    >
      <div className="flex items-center gap-1.5 border-b border-rebar pb-2">
        <input
          type="search"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder="Filter…"
          aria-label="Filter outliner"
          data-testid="outliner-filter"
          className="min-w-0 flex-1 rounded border border-rebar bg-void px-1.5 py-1 text-[10px] text-bone placeholder:text-shroud"
        />
        <button
          onClick={() => setCompact((c) => !c)}
          aria-pressed={compact}
          title="Toggle compact density"
          data-testid="outliner-density-toggle"
          className={`shrink-0 rounded border px-1.5 py-1 text-[10px] ${
            compact ? "border-spire text-spire" : "border-rebar text-fog hover:border-wet-steel"
          }`}
        >
          ≡
        </button>
      </div>

      <OrganizationsSection
        orgs={orgs}
        filtered={filteredOrgs}
        filterText={filterText}
        compact={compact}
        selection={selection}
        setSelection={setSelection}
      />

      <CommunitiesSection
        loaded={communitiesData !== null}
        communities={communities}
        filtered={filteredCommunities}
        filterText={filterText}
        compact={compact}
        selection={selection}
        setSelection={setSelection}
      />

      <FactionsSection
        factions={factions}
        filtered={filteredFactions}
        filterText={filterText}
        compact={compact}
        factionFilter={factionFilter}
        selectFaction={selectFaction}
      />
    </nav>
  );
}

function EmptyRow({ text }: { text: string }): React.JSX.Element {
  return <p className="px-2 py-1 text-[10px] italic text-shroud">{text}</p>;
}
