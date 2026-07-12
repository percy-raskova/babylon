/**
 * SpeedControls — the real speed cluster (architecture §1.2's
 * `TimeControls` → `SpeedControls` rewrite row; architecture §4.1;
 * DESIGN_BIBLE §5.1's "identity/date/speed cluster", §5.3's "1/2/3 =
 * speed"). Wraps `TimeControls` verbatim (keeps `time-controls`,
 * `time-status`, `time-resume` testids untouched) and adds the
 * "⏸ ▶1 ▶▶2 ▶▶▶5" speed row on top — `setSpeed` is valid in any status, so
 * these buttons stay live even mid-resolve/mid-delay.
 *
 * Selected speed uses the shared gold inverse-video grammar
 * (`installerKit.keyButtonClass`, DESIGN_BIBLE §9b). A small square blip
 * pulses (`tick-pulse`, one-shot, integration-ledger.md's Juice Pass) on
 * every tick advance — keyed on the tick value itself so React remounts
 * (and thus restarts) the animation rather than relying on a CSS
 * re-trigger hack.
 */

import { useStore } from "@/store";
import type { TimeSpeed } from "@/store/slices/timeSlice";
import { useSpeedShortcut } from "@/hooks/useSpeedShortcut";
import { TimeControls } from "@/components/shell/TimeControls";
import { keyButtonClass } from "./installerKit";

interface SpeedControlsProps {
  gameId: string;
}

const SPEEDS: { value: TimeSpeed; label: string }[] = [
  { value: 1, label: "▶1" },
  { value: 2, label: "▶▶2" },
  { value: 5, label: "▶▶▶5" },
];

export function SpeedControls({ gameId }: SpeedControlsProps): React.JSX.Element {
  useSpeedShortcut();

  const speed = useStore((s) => s.time.speed);
  const setSpeed = useStore((s) => s.time.setSpeed);
  const tick = useStore((s) => s.world.snapshot?.tick);

  return (
    <div className="flex items-center gap-2" data-testid="speed-controls">
      <TimeControls gameId={gameId} />
      {tick !== undefined && (
        <span
          key={tick}
          data-testid="tick-pulse-dot"
          aria-hidden="true"
          className="tick-pulse h-1.5 w-1.5 shrink-0 bg-accent-gold"
        />
      )}
      <div
        className="flex items-center gap-1 border-l border-ksbc-muted-1 pl-2"
        role="group"
        aria-label="Speed"
      >
        {SPEEDS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setSpeed(value)}
            aria-pressed={speed === value}
            title={`${value}x speed (key ${SPEEDS.findIndex((s) => s.value === value) + 1})`}
            data-testid={`speed-${value}`}
            className={keyButtonClass(speed === value, "px-1.5 py-0.5 text-[10px]")}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
