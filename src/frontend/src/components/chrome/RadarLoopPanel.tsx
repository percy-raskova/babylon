/**
 * RadarLoopPanel — the RADAR LOOP tick scrubber (Program 17 Wave 3,
 * Frontend-W3R3): replays a map lens through its recorded history.
 *
 * DESIGN_BIBLE.md §11 law 2 (binding): replay frames are HARD CUTS between
 * ticks — no tweening/interpolation. Play mode here is a fixed-interval
 * frame-STEPPER (`PLAY_INTERVAL_MS`, ~3fps), not a smooth animation; it
 * honors `prefers-reduced-motion` by disabling itself entirely
 * (scrub-only stays available — dragging the range input is not
 * "animation", it's discrete input, same reasoning `criticalPulse.ts`'s
 * `prefersReducedMotion` guard already applies elsewhere in this module
 * family).
 *
 * Availability gates on the map's CURRENTLY ACTIVE lens
 * (`lib/lens.ts`'s `isReplayableLens`) — only 4 of the 11 `MAP_METRICS`
 * have a genuine persisted per-tick history (`MAP_HISTORY_REPLAYABLE_METRICS`,
 * mirroring the backend's `map_contract.py` tuple of the same name); every
 * other lens shows an honest hint naming the 4 that ARE replayable
 * (Constitution III.11 — no silently-broken scrubber).
 *
 * Mounted via `FloatingPanel` (anchor="free") in `AppShell`'s existing
 * right-column chrome stack, alongside `EventTray`/`ObjectivesTray`/
 * `BifurcationGauge` — the same "AppShell chrome line" append point,
 * `ui.chrome.radarLoopOpen`/`toggleRadarLoop` mirroring
 * `bifurcationOpen`/`toggleBifurcation` exactly.
 *
 * The map-fill side of this feature (`DeckGLMap`'s `replay` prop,
 * `MapStage.tsx` composing it from this slice + the active lens) lives
 * elsewhere — this component only owns the scrubber UI and the
 * `mapReplay` slice's `enter`/`exit`/`scrubTo`/`step` calls.
 */

import { useEffect, useState } from "react";
import { useStore, type MapReplayStatus } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { keyButtonClass } from "./installerKit";
import { prefersReducedMotion } from "@/components/map/layers/criticalPulse";
import {
  lensMetricName,
  isReplayableLens,
  lensLegendLabel,
  MAP_HISTORY_REPLAYABLE_METRICS,
  type Lens,
} from "@/lib/lens";
import type { MapHistoryFrame } from "@/types/game";

interface RadarLoopPanelProps {
  gameId: string;
}

/** ~3fps frame-stepper — a slideshow of hard cuts (DESIGN_BIBLE.md §11 law 2), never a tween. */
const PLAY_INTERVAL_MS = 333;

/** The 4 replayable lenses' display labels, for the honest "not available for this lens" hint. */
const REPLAYABLE_LENS_LABELS = MAP_HISTORY_REPLAYABLE_METRICS.map((metric) =>
  lensLegendLabel(metric === "heat" ? { kind: "heat" } : { kind: "metric", metric }),
);

/** The honest hint copy for a lens with no persisted history. Extracted for the cognitive-complexity budget. */
function unavailableHint(lens: Lens): string {
  return (
    `${lensLegendLabel(lens)} has no persisted history — 4 lenses are replayable: ` +
    `${REPLAYABLE_LENS_LABELS.join(", ")}.`
  );
}

/** Fixed-interval frame-stepper: advances `step(1)` every `PLAY_INTERVAL_MS` while `playing`, auto-pausing at the last frame. */
function usePlayback(playing: boolean, setPlaying: (v: boolean) => void): void {
  useEffect(() => {
    if (!playing) return undefined;
    const interval = window.setInterval(() => {
      const current = useStore.getState().mapReplay;
      if (current.currentIndex >= current.frames.length - 1) {
        setPlaying(false);
        return;
      }
      current.step(1);
    }, PLAY_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [playing, setPlaying]);
}

/** The loading/error/empty status line — one honest message per `MapReplayStatus`, or `null` once real frames exist. Extracted for `ReplayBody`'s cognitive-complexity budget. */
function ReplayStatusMessage({
  status,
  frameCount,
  error,
}: {
  status: MapReplayStatus;
  frameCount: number;
  error: string | null;
}): React.JSX.Element | null {
  if (status === "loading") return <p data-testid="radar-loop-loading">Loading history…</p>;
  if (status === "error") {
    return (
      <p role="alert" data-testid="radar-loop-error" className="text-laser">
        {error}
      </p>
    );
  }
  if (status === "ready" && frameCount === 0) {
    return <p data-testid="radar-loop-empty">No history recorded for this metric yet.</p>;
  }
  return null;
}

interface ReplayScrubberProps {
  frames: MapHistoryFrame[];
  currentIndex: number;
  capped: boolean;
  liveTickAvailable: number | null;
  reducedMotion: boolean;
  playing: boolean;
  setPlaying: (updater: (p: boolean) => boolean) => void;
  scrubTo: (index: number) => void;
}

/** The tick readout + range scrubber + play/step controls — only rendered once real frames exist. Extracted for `ReplayBody`'s cognitive-complexity budget. */
function ReplayScrubber({
  frames,
  currentIndex,
  capped,
  liveTickAvailable,
  reducedMotion,
  playing,
  setPlaying,
  scrubTo,
}: ReplayScrubberProps): React.JSX.Element | null {
  const currentFrame = frames[currentIndex];
  if (!currentFrame) return null;

  return (
    <>
      <p data-testid="radar-loop-tick-readout">
        Tick {currentFrame.tick} ({currentIndex + 1}/{frames.length}) · window {frames[0]?.tick}–
        {frames.at(-1)?.tick}
      </p>
      <p className="text-ksbc-muted-2">
        County-grain: every hex/territory in a county shows that county's value.
      </p>
      {capped && <p data-testid="radar-loop-capped">History window capped at 128 ticks.</p>}
      <input
        type="range"
        data-testid="radar-loop-scrubber"
        min={0}
        max={frames.length - 1}
        value={currentIndex}
        onChange={(e) => scrubTo(Number(e.target.value))}
        style={{ accentColor: "var(--ksbc-accent-gold)" }}
        className="w-full"
      />
      <div className="flex items-center gap-1">
        <button
          type="button"
          data-testid="radar-loop-step-back"
          onClick={() => scrubTo(currentIndex - 1)}
          className={keyButtonClass(false, "px-1.5 py-0.5")}
        >
          ◀
        </button>
        <button
          type="button"
          data-testid="radar-loop-play-pause"
          disabled={reducedMotion}
          aria-label={playing ? "Pause" : "Play"}
          onClick={() => setPlaying((p) => !p)}
          className={keyButtonClass(playing, "px-1.5 py-0.5")}
        >
          {playing ? "❚❚" : "▶"}
        </button>
        <button
          type="button"
          data-testid="radar-loop-step-forward"
          onClick={() => scrubTo(currentIndex + 1)}
          className={keyButtonClass(false, "px-1.5 py-0.5")}
        >
          ▶
        </button>
      </div>
      {liveTickAvailable !== null && (
        <p data-testid="radar-loop-live-tick-hint">Live tick {liveTickAvailable} available.</p>
      )}
    </>
  );
}

function ReplayBody({ gameId }: { gameId: string }): React.JSX.Element {
  const status = useStore((s) => s.mapReplay.status);
  const frames = useStore((s) => s.mapReplay.frames);
  const currentIndex = useStore((s) => s.mapReplay.currentIndex);
  const capped = useStore((s) => s.mapReplay.capped);
  const error = useStore((s) => s.mapReplay.error);
  const liveTickAvailable = useStore((s) => s.mapReplay.liveTickAvailable);
  const scrubTo = useStore((s) => s.mapReplay.scrubTo);
  const exitReplay = useStore((s) => s.mapReplay.exit);
  const enterReplay = useStore((s) => s.mapReplay.enter);
  const metric = useStore((s) => s.mapReplay.metric);
  const tick = useStore((s) => s.world.snapshot?.tick);
  const noteLiveTick = useStore((s) => s.mapReplay.noteLiveTick);

  const [playing, setPlaying] = useState(false);
  usePlayback(playing, setPlaying);

  useEffect(() => {
    if (tick !== undefined) noteLiveTick(tick);
  }, [tick, noteLiveTick]);

  const reducedMotion = prefersReducedMotion();

  function handleExit(): void {
    setPlaying(false);
    exitReplay();
  }

  return (
    <div className="flex flex-col gap-1 p-2 text-[9px]">
      <span
        data-testid="radar-loop-replay-badge"
        className="w-fit rounded-none bg-accent-crimson px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-void"
      >
        Replay — showing the past
      </span>

      <ReplayStatusMessage status={status} frameCount={frames.length} error={error} />

      {status === "ready" && (
        <ReplayScrubber
          frames={frames}
          currentIndex={currentIndex}
          capped={capped}
          liveTickAvailable={liveTickAvailable}
          reducedMotion={reducedMotion}
          playing={playing}
          setPlaying={setPlaying}
          scrubTo={scrubTo}
        />
      )}

      <div className="flex gap-1">
        {status === "error" && metric && (
          <button
            type="button"
            data-testid="radar-loop-retry"
            onClick={() => void enterReplay(gameId, metric)}
            className={keyButtonClass(false, "px-1.5 py-0.5")}
          >
            Retry
          </button>
        )}
        <button
          type="button"
          data-testid="radar-loop-exit"
          onClick={handleExit}
          className={keyButtonClass(false, "px-1.5 py-0.5")}
        >
          Exit Replay
        </button>
      </div>
    </div>
  );
}

export function RadarLoopPanel({ gameId }: RadarLoopPanelProps): React.JSX.Element {
  const radarLoopOpen = useStore((s) => s.ui.chrome.radarLoopOpen);
  const toggleRadarLoop = useStore((s) => s.ui.toggleRadarLoop);
  const lens = useStore((s) => s.map.lens);
  const active = useStore((s) => s.mapReplay.active);
  const enterReplay = useStore((s) => s.mapReplay.enter);

  const metric = lensMetricName(lens);
  const replayable = isReplayableLens(lens);

  return (
    <FloatingPanel
      anchor="free"
      title="Radar Loop"
      collapsed={!radarLoopOpen}
      onToggle={toggleRadarLoop}
      testId="radar-loop-panel"
    >
      {active ? (
        <ReplayBody gameId={gameId} />
      ) : (
        <div className="flex flex-col gap-1 p-2 text-[9px]">
          {replayable && metric ? (
            <>
              <p>{lensLegendLabel(lens)} — replay its recorded history.</p>
              <button
                type="button"
                data-testid="radar-loop-start"
                onClick={() => void enterReplay(gameId, metric)}
                className={keyButtonClass(false, "px-1.5 py-0.5")}
              >
                Start Replay
              </button>
            </>
          ) : (
            <p data-testid="radar-loop-unavailable-hint" className="text-ksbc-muted-2">
              {unavailableHint(lens)}
            </p>
          )}
        </div>
      )}
    </FloatingPanel>
  );
}
