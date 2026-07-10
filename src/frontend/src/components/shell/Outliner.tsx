/**
 * Left Outliner — collapsible orgs / communities / factions lists.
 * Clicking a row drives the Inspector + map highlight via
 * `map.setSelection`. Factions read off `panels.map`'s balkanization
 * block; `MapPanel` owns that panel's mount/fetch lifecycle (both it and
 * this component are always mounted together for AppShell's lifetime, so
 * there is exactly one owner — see `panelFactory.ts`'s docstring on the
 * boolean (not refcounted) `mounted` flag).
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { factionsFromMapData } from "@/lib/mapMetadata";
import { OutlinerSection } from "./OutlinerSection";
import { OutlinerRow } from "./OutlinerRow";

interface OutlinerProps {
  gameId: string;
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

  useEffect(() => {
    setCommunitiesMounted(true);
    void fetchCommunities(gameId);
    return () => setCommunitiesMounted(false);
  }, [gameId, fetchCommunities, setCommunitiesMounted]);

  const communities = communitiesData?.communities ?? [];
  const factions = factionsFromMapData(mapData);

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
      <OutlinerSection title="Organizations" count={orgs.length}>
        {orgs.length === 0 && <EmptyRow text="No organizations in this session." />}
        {orgs.map((org) => (
          <OutlinerRow
            key={org.id}
            label={org.short_name ?? org.name}
            sublabel={org.org_type}
            selected={selection?.kind === "org" && selection.id === org.id}
            onClick={() => setSelection({ kind: "org", id: org.id })}
          />
        ))}
      </OutlinerSection>

      <OutlinerSection title="Communities" count={communities.length}>
        {communitiesData === null && <EmptyRow text="Communities not loaded yet." />}
        {communitiesData !== null && communities.length === 0 && (
          <EmptyRow text="No communities formed yet." />
        )}
        {communities.map((c) => (
          <OutlinerRow
            key={c.id}
            label={c.dominant_role ?? c.id}
            sublabel={`${c.member_count} members`}
            selected={selection?.kind === "community" && selection.id === c.id}
            onClick={() => setSelection({ kind: "community", id: c.id })}
          />
        ))}
      </OutlinerSection>

      <OutlinerSection title="Factions" count={factions.length}>
        {factions.length === 0 && <EmptyRow text="No faction data — collapse layer unseeded." />}
        {factions.map((f) => (
          <OutlinerRow
            key={f.id}
            label={f.id}
            sublabel={f.colonial_stance}
            selected={factionFilter === f.id}
            onClick={() => selectFaction(f.id)}
          />
        ))}
      </OutlinerSection>
    </nav>
  );
}

function EmptyRow({ text }: { text: string }): React.JSX.Element {
  return <p className="px-2 py-1 text-[10px] italic text-shroud">{text}</p>;
}
