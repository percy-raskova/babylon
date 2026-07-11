/**
 * B4 transport controls — Pause/Step/Play buttons + a state indicator.
 * Spacebar toggling is wired globally by `useSpacebarShortcut`
 * (`GameRoute`); this component is the visible surface for the same
 * `timeSlice` state machine.
 *
 * SKIN (Design Bible §9b): buttons compose `installerKit`'s shared
 * button-as-key grammar so this row matches the `SpeedControls` cluster
 * that hosts it — gold inverse-video while playing (the one selection
 * grammar), crimson urgent key for Resume. Status text uses the ksbc
 * role ramp (grey idle / green running / gold working / crimson urgent).
 */

import { useStore } from "@/store";
import type { TimeStatus } from "@/store";
import { keyButtonClass, keyButtonUrgentClass } from "@/components/chrome/installerKit";

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
  paused: "text-ksbc-muted-2",
  playing: "text-ksbc-green-bright",
  resolving: "text-accent-gold",
  autopaused: "text-accent-crimson",
  error: "text-accent-crimson",
};

const KEY_SIZE = "px-2.5 py-1 text-[10px] disabled:opacity-40";

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
        className={keyButtonClass(false, KEY_SIZE)}
      >
        Step
      </button>
      <button
        onClick={() => (isPlayingIntent ? pause() : void play(gameId))}
        disabled={!isPaused && !isPlayingIntent}
        title="Play/Pause (spacebar)"
        className={keyButtonClass(isPlayingIntent, KEY_SIZE)}
      >
        {isPlayingIntent ? "Pause" : "Play"}
      </button>
      {needsResume && (
        <button
          onClick={resume}
          className={keyButtonUrgentClass(KEY_SIZE)}
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
        <span role="alert" className="text-[10px] text-accent-crimson">
          {errorMessage}
        </span>
      )}
    </div>
  );
}
