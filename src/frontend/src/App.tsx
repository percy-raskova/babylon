/**
 * Cockpit app shell (spec-110 B1) — scaffold only.
 *
 * Full-viewport dark layout with five named placeholder regions
 * (StatusBar / Outliner / Map / Dock / BottomStrip) plus a tiny
 * `/health` fetch indicator. No game logic, no map rendering yet —
 * that lands in B2.
 */

import { useEffect, useState } from "react";

type HealthStatus = "checking" | "ok" | "unreachable";

/** Poll the Django `/health` endpoint once on mount and report status. */
function useHealthStatus(): HealthStatus {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    async function checkHealth(): Promise<void> {
      try {
        const response = await fetch("/health");
        if (!cancelled) {
          setStatus(response.ok ? "ok" : "unreachable");
        }
      } catch {
        if (!cancelled) {
          setStatus("unreachable");
        }
      }
    }

    void checkHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}

const HEALTH_LABELS: Record<HealthStatus, string> = {
  checking: "checking…",
  ok: "online",
  unreachable: "unreachable",
};

const HEALTH_DOT_CLASSES: Record<HealthStatus, string> = {
  checking: "bg-amber-400",
  ok: "bg-emerald-400",
  unreachable: "bg-red-500",
};

function HealthIndicator(): React.JSX.Element {
  const status = useHealthStatus();
  const label = HEALTH_LABELS[status];
  const dotClass = HEALTH_DOT_CLASSES[status];

  return (
    <div data-testid="health-indicator" data-status={status} className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full ${dotClass}`} aria-hidden="true" />
      <span className="text-xs uppercase tracking-widest text-neutral-400">{label}</span>
    </div>
  );
}

export default function App(): React.JSX.Element {
  return (
    <div className="grid h-screen w-screen grid-cols-[240px_1fr_320px] grid-rows-[48px_1fr_140px] bg-[#06070b] text-[#d8dce0]">
      <header
        data-testid="region-statusbar"
        aria-label="StatusBar"
        className="col-span-3 flex items-center justify-between border-b border-neutral-800 px-4"
      >
        <span className="text-sm font-semibold tracking-[4px]">BABYLON COCKPIT</span>
        <HealthIndicator />
      </header>

      <nav
        data-testid="region-outliner"
        aria-label="Outliner"
        className="row-start-2 overflow-y-auto border-r border-neutral-800 p-3"
      />

      <main
        data-testid="region-map"
        aria-label="Map"
        className="row-start-2 flex items-center justify-center overflow-hidden"
      />

      <aside
        data-testid="region-dock"
        aria-label="Dock"
        className="row-start-2 overflow-y-auto border-l border-neutral-800 p-3"
      />

      <footer
        data-testid="region-bottomstrip"
        aria-label="BottomStrip"
        className="col-span-3 row-start-3 border-t border-neutral-800 p-3"
      />
    </div>
  );
}
