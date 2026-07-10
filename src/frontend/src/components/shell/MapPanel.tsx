/**
 * Center — the persistent map. Mounts the B2-ported `DeckGLMap` as a
 * controlled component wired to `mapSlice` (lens/selection/faction
 * filter/viewport) and `panels.map` (the fetched GeoJSON). Sole owner of
 * `panels.map`'s mount/fetch lifecycle — see `Outliner.tsx`'s docstring.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { DeckGLMap } from "@/components/map/DeckGLMap";
import type { MapFeatureCollectionWithMetadata } from "@/lib/mapMetadata";

interface MapPanelProps {
  gameId: string;
}

export function MapPanel({ gameId }: MapPanelProps): React.JSX.Element {
  const snapshot = useStore((s) => s.world.snapshot);
  const mapData = useStore((s) => s.panels.map.data);
  const fetchMap = useStore((s) => s.panels.map.fetch);
  const setMapMounted = useStore((s) => s.panels.map.setMounted);
  const framing = useStore((s) => s.map.framing);
  const lens = useStore((s) => s.map.lens);
  const setLens = useStore((s) => s.map.setLens);
  const factionFilter = useStore((s) => s.map.factionFilter);
  const setFactionFilter = useStore((s) => s.map.setFactionFilter);
  const setSelection = useStore((s) => s.map.setSelection);

  useEffect(() => {
    setMapMounted(true);
    return () => setMapMounted(false);
  }, [gameId, setMapMounted]);

  useEffect(() => {
    // Also refetches on `framing` change — the endpoint URL itself is
    // `?zoom=${framing}` (`panels/index.ts`), so a LOD change needs a
    // fresh fetch, not just the tick-advance fan-out.
    void fetchMap(gameId);
  }, [gameId, framing, fetchMap]);

  return (
    <main
      data-testid="region-map"
      aria-label="Map"
      className="row-start-2 flex min-w-0 flex-col overflow-hidden"
    >
      {!snapshot ? (
        <div className="flex flex-1 items-center justify-center text-[12px] italic text-shroud">
          No world state loaded yet.
        </div>
      ) : (
        <DeckGLMap
          snapshot={snapshot}
          mapData={mapData as MapFeatureCollectionWithMetadata | null}
          lens={lens}
          onLensChange={setLens}
          factionFilter={factionFilter}
          onFactionFilterChange={setFactionFilter}
          onTerritoryClick={(territoryId) => setSelection({ kind: "hex", id: territoryId })}
        />
      )}
    </main>
  );
}
