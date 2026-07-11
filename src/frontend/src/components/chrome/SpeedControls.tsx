/**
 * SpeedControls — the real speed cluster (architecture §1.2's
 * `TimeControls` → `SpeedControls` rewrite row; architecture §4.1;
 * DESIGN_BIBLE §5.1's "identity/date/speed cluster", §5.3's "1/2/3 =
 * speed"). Wraps `TimeControls` verbatim (keeps `time-controls`,
 * `time-status`, `time-resume` testids untouched) and adds the
 * "⏸ ▶1 ▶▶2 ▶▶▶5" speed row on top — `setSpeed` is valid in any status, so
 * these buttons stay live even mid-resolve/mid-delay.
 */

import { useStore } from "@/store";
import type { TimeSpeed } from "@/store/slices/timeSlice";
import { useSpeedShortcut } from "@/hooks/useSpeedShortcut";
import { TimeControls } from "@/components/shell/TimeControls";

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

  return (
    <div className="flex items-center gap-2" data-testid="speed-controls">
      <TimeControls gameId={gameId} />
      <div
        className="flex items-center gap-1 border-l border-rebar pl-2"
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
            className={`rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-widest ${
              speed === value
                ? "border-spire text-spire"
                : "border-wet-steel text-fog hover:border-spire"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
