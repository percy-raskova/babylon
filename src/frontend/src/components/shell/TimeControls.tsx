/**
 * B4 transport controls — Pause/Step/Play buttons + a state indicator.
 * Spacebar toggling is wired globally by `useSpacebarShortcut`
 * (`GameRoute`); this component is the visible surface for the same
 * `timeSlice` state machine.
 */

import { useStore } from "@/store";
import type { TimeStatus } from "@/store";

interface TimeControlsProps {
  gameId: string;
}

const STATUS_LABEL: Record<TimeStatus, string> = {
  paused: "PAUSED",
  playing: "PLAYING",
  resolving: "RESOLVING…",
  autopaused: "AUTOPAUSED",
  error: "ERROR",
};

const STATUS_COLOR: Record<TimeStatus, string> = {
  paused: "text-fog",
  playing: "text-spire",
  resolving: "text-heat",
  autopaused: "text-heat",
  error: "text-laser",
};

const BUTTON_BASE =
  "rounded border px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest disabled:cursor-not-allowed disabled:opacity-40";

export function TimeControls({ gameId }: TimeControlsProps): React.JSX.Element {
  const status = useStore((s) => s.time.status);
  const errorMessage = useStore((s) => s.time.errorMessage);
  const step = useStore((s) => s.time.step);
  const play = useStore((s) => s.time.play);
  const pause = useStore((s) => s.time.pause);
  const resume = useStore((s) => s.time.resume);

  const playIntent = useStore((s) => s.time.playIntent);

  const isPaused = status === "paused";
  // Under Play with real multi-second resolves the machine spends almost all
  // wall time in `resolving`; the pause control must stay reachable there —
  // pause() registers a stop-request the serialized loop honors after the
  // in-flight resolve settles (timeSlice.pause docstring).
  const isPlayingIntent = status === "playing" || (status === "resolving" && playIntent);
  const needsResume = status === "autopaused" || status === "error";

  return (
    <div className="flex items-center gap-2" data-testid="time-controls">
      <button
        onClick={() => void step(gameId)}
        disabled={!isPaused}
        title="Step — resolve exactly one tick"
        className={`${BUTTON_BASE} border-wet-steel text-fog hover:border-spire`}
      >
        Step
      </button>
      <button
        onClick={() => (isPlayingIntent ? pause() : void play(gameId))}
        disabled={!isPaused && !isPlayingIntent}
        title="Play/Pause (spacebar)"
        className={`${BUTTON_BASE} ${
          isPlayingIntent
            ? "border-spire text-spire"
            : "border-wet-steel text-fog hover:border-spire"
        }`}
      >
        {isPlayingIntent ? "Pause" : "Play"}
      </button>
      {needsResume && (
        <button
          onClick={resume}
          className={`${BUTTON_BASE} border-heat text-heat`}
          data-testid="time-resume"
        >
          Resume
        </button>
      )}
      <span
        data-testid="time-status"
        className={`text-[10px] font-mono uppercase tracking-widest ${STATUS_COLOR[status]}`}
      >
        {STATUS_LABEL[status]}
      </span>
      {status === "error" && errorMessage && (
        <span role="alert" className="text-[10px] text-laser">
          {errorMessage}
        </span>
      )}
    </div>
  );
}
