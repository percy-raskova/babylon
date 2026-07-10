/**
 * Cockpit app shell (spec-110 B1 scaffold, Cold Collapse tokens ported B2).
 *
 * Full-viewport dark layout with five named placeholder regions
 * (StatusBar / Outliner / Map / Dock / BottomStrip) plus a tiny
 * `/health` fetch indicator. Colors are now the ratified Cold Collapse
 * canon tokens (`index.css`, Constitution VIII) rather than B1's
 * placeholder grays — every color here is a named token
 * (`bg-void`/`text-bone`/`border-rebar`/…), never a raw hex literal.
 * No game logic, no map mounted, no store/routing wiring yet — those are
 * B3's (stores + shell layout + routing, orchestrator-supervised).
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
  checking: "bg-heat",
  ok: "bg-solidarity",
  unreachable: "bg-laser",
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
    <div className="grid h-screen w-screen grid-cols-[240px_1fr_320px] grid-rows-[48px_1fr_140px] bg-void text-bone">
      <header
        data-testid="region-statusbar"
        aria-label="StatusBar"
        className="col-span-3 flex items-center justify-between border-b border-rebar px-4"
      >
        <span className="text-sm font-semibold tracking-[4px]">BABYLON COCKPIT</span>
        <HealthIndicator />
      </header>

      <nav
        data-testid="region-outliner"
        aria-label="Outliner"
        className="row-start-2 overflow-y-auto border-r border-rebar p-3"
      />

      <main
        data-testid="region-map"
        aria-label="Map"
        className="row-start-2 flex items-center justify-center overflow-hidden"
      />

      <aside
        data-testid="region-dock"
        aria-label="Dock"
        className="row-start-2 overflow-y-auto border-l border-rebar p-3"
      />

      <footer
        data-testid="region-bottomstrip"
        aria-label="BottomStrip"
        className="col-span-3 row-start-3 border-t border-rebar p-3"
      />
    </div>
  );
}
