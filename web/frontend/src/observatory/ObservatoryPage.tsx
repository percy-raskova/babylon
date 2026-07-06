/**
 * Observatory page shell — the dev-facing debug dashboard over the simulation
 * database. Probes the feature flag first (the backend 404s the whole surface
 * when OBSERVATORY_ENABLED is off); then lists sessions and browses series.
 *
 * Lazily loaded from App.tsx so it adds no weight to the main game bundle.
 */

import { useEffect, useState } from "react";
import { fetchSessions, fetchStatus } from "./api";
import { SessionPicker } from "./SessionPicker";
import { SeriesBrowser } from "./SeriesBrowser";
import type { ObservatorySession } from "./types";

type LoadState = "checking" | "unavailable" | "ready";

export default function ObservatoryPage() {
  const [loadState, setLoadState] = useState<LoadState>("checking");
  const [sessions, setSessions] = useState<ObservatorySession[]>([]);
  const [selected, setSelected] = useState<ObservatorySession | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const status = await fetchStatus();
      if (!active) return;
      if (status === null || !status.enabled) {
        setLoadState("unavailable");
        return;
      }
      const list = await fetchSessions();
      if (!active) return;
      setSessions(list);
      setLoadState("ready");
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col bg-void text-bone">
      <header className="flex shrink-0 items-center justify-between border-b border-soot bg-dark-metal px-6 py-4">
        <div>
          <h1 className="text-lg font-bold tracking-widest text-gold">OBSERVATORY</h1>
          <p className="mt-0.5 text-xs text-ash">
            Read-only debug dashboard over the simulation database
          </p>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-auto">
        {loadState === "checking" && (
          <div role="status" className="p-8 text-center text-sm text-ash">
            Connecting to the simulation database…
          </div>
        )}

        {loadState === "unavailable" && (
          <div role="alert" className="p-8 text-center text-sm text-ash">
            The Observatory is disabled or unavailable. It is enabled in development (
            <code className="text-silver">OBSERVATORY_ENABLED</code>) and requires the simulation
            database.
          </div>
        )}

        {loadState === "ready" && selected === null && (
          <SessionPicker sessions={sessions} onSelect={setSelected} />
        )}

        {loadState === "ready" && selected !== null && (
          <SeriesBrowser session={selected} onBack={() => setSelected(null)} />
        )}
      </main>
    </div>
  );
}
