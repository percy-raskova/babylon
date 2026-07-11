/**
 * CriticalEventModal — chrome stub, placeholder mount point (architecture
 * §4.2's Paradox-style modal rendered whenever `time.status ===
 * "autopaused"`; net-new, gives the existing autopause machinery its
 * missing face). v1 renders a minimal honest surface — Lane E owns the
 * real CTAs ("Open Wire" / "Resume") reading `autopauseEventIds`.
 */

import { useStore } from "@/store";

interface CriticalEventModalProps {
  gameId: string;
}

export function CriticalEventModal(_props: CriticalEventModalProps): React.JSX.Element | null {
  const status = useStore((s) => s.time.status);

  if (status !== "autopaused") return null;

  return (
    <div
      data-testid="critical-event-modal"
      role="alertdialog"
      className="pointer-events-auto absolute inset-0 flex items-center justify-center bg-void/60"
    >
      <div className="rounded border border-heat bg-concrete p-4 text-[11px] text-fog">
        Autopaused — a critical event needs attention.
      </div>
    </div>
  );
}
