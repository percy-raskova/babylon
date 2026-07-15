/**
 * MapStage — Layer 0 of the shell (architecture §0/§1.1): `DeckGLMap` at
 * `absolute inset-0`, always mounted, the only scroll/drag surface. Sole
 * owner of `panels.map`'s mount/fetch lifecycle (unchanged from the
 * former `MapPanel.tsx`, which this file replaces one-for-one — see
 * `Outliner.tsx`'s docstring for why there is exactly one owner).
 *
 * Keeps `data-testid="region-map"`. `DeckGLMap`'s props/interface was frozen
 * under the Lane A/Lane B contract (architecture §3.3) through spec-113; Wave
 * 3 §11's gradient-wind lens is the first amendment to that freeze — it adds
 * one optional `gameId` prop (MapStage already had it) so `DeckGLMap` can
 * fetch `GET /field_state/` itself when the `field_flow` lens is active.
 * Program 17 Wave 3 (Frontend-W3R3)'s RADAR LOOP tick scrubber is the
 * second amendment — `resolveMapReplayOverride` below composes the
 * `mapReplay` slice + the active lens into `DeckGLMap`'s `replay` prop, so
 * this is the ONE place that decision is made (`RadarLoopPanel.tsx` only
 * drives `mapReplay.enter`/`exit`/`scrubTo`/`step`, never the map itself).
 */

import { useEffect, useMemo } from "react";
import { useStore } from "@/store";
import { DeckGLMap, type MapReplayFillOverride } from "@/components/map/DeckGLMap";
import type { MapFeatureCollectionWithMetadata } from "@/lib/mapMetadata";
import { lensMetricName, type MapMetric } from "@/lib/lens";
import type { MapHistoryFrame } from "@/types/game";
import type { MapReplayStatus } from "@/store";

interface MapStageProps {
  gameId: string;
}

/**
 * The map's replay-fill override for `DeckGLMap`'s `replay` prop (Program
 * 17 Wave 3, Frontend-W3R3) — `null` whenever replay is inactive/loading/
 * erroring, OR the active lens's metric doesn't match the replay window's
 * own metric (an honest silent revert to live fill if the player switches
 * lenses mid-replay, never a crash). Extracted to a top-level function
 * (mirrors `DeckGLMap.tsx`'s own many top-level pure helpers) so
 * `MapStage`'s render body stays a plain `useMemo` call.
 */
function resolveMapReplayOverride(
  active: boolean,
  status: MapReplayStatus,
  replayMetric: MapMetric | null,
  frames: MapHistoryFrame[],
  currentIndex: number,
  lensMetric: MapMetric | null,
): MapReplayFillOverride | null {
  if (!active || status !== "ready" || replayMetric === null) return null;
  if (lensMetric !== replayMetric) return null;
  const frame = frames[currentIndex];
  if (!frame) return null;
  return { metric: replayMetric, valuesByCounty: frame.values };
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

  const replayActive = useStore((s) => s.mapReplay.active);
  const replayStatus = useStore((s) => s.mapReplay.status);
  const replayMetric = useStore((s) => s.mapReplay.metric);
  const replayFrames = useStore((s) => s.mapReplay.frames);
  const replayIndex = useStore((s) => s.mapReplay.currentIndex);
  const replay = useMemo(
    () =>
      resolveMapReplayOverride(
        replayActive,
        replayStatus,
        replayMetric,
        replayFrames,
        replayIndex,
        lensMetricName(lens),
      ),
    [replayActive, replayStatus, replayMetric, replayFrames, replayIndex, lens],
  );

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
          gameId={gameId}
          lens={lens}
          onLensChange={setLens}
          factionFilter={factionFilter}
          onFactionFilterChange={setFactionFilter}
          onTerritoryClick={(territoryId, inline) =>
            setSelection({ kind: "hex", id: territoryId, inline })
          }
          framing={framing}
          onFramingChange={setFraming}
          replay={replay}
        />
      )}
    </main>
  );
}
