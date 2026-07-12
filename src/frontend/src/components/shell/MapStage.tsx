/**
 * MapStage — Layer 0 of the shell (architecture §0/§1.1): `DeckGLMap` at
 * `absolute inset-0`, always mounted, the only scroll/drag surface. Sole
 * owner of `panels.map`'s mount/fetch lifecycle (unchanged from the
 * former `MapPanel.tsx`, which this file replaces one-for-one — see
 * `Outliner.tsx`'s docstring for why there is exactly one owner).
 *
 * Keeps `data-testid="region-map"`. `DeckGLMap`'s props/interface are
 * unchanged — this is the Lane A/Lane B contract (architecture §3.3).
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { DeckGLMap } from "@/components/map/DeckGLMap";
import type { MapFeatureCollectionWithMetadata } from "@/lib/mapMetadata";

interface MapStageProps {
  gameId: string;
}

export function MapStage({ gameId }: MapStageProps): React.JSX.Element {
  const snapshot = useStore((s) => s.world.snapshot);
  const mapData = useStore((s) => s.panels.map.data);
  const fetchMap = useStore((s) => s.panels.map.fetch);
  const setMapMounted = useStore((s) => s.panels.map.setMounted);
  const framing = useStore((s) => s.map.framing);
  const setFraming = useStore((s) => s.map.setFraming);
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
    <main data-testid="region-map" aria-label="Map" className="absolute inset-0 overflow-hidden">
      {!snapshot ? (
        <div className="flex h-full items-center justify-center text-[12px] italic text-shroud">
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
          onTerritoryClick={(territoryId, inline) =>
            setSelection({ kind: "hex", id: territoryId, inline })
          }
          framing={framing}
          onFramingChange={setFraming}
        />
      )}
    </main>
  );
}
