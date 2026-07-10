/**
 * Observatory page shell — the dev-facing debug dashboard over the simulation
 * database. Probes the feature flag first (the backend 404s the whole surface
 * when OBSERVATORY_ENABLED is off — the honest "disabled" state, Constitution
 * III.11); then lists sessions and browses series + deep diagnostic panes,
 * for the selected source (live | archive).
 *
 * Ported from `web/frontend/src/observatory/ObservatoryPage.tsx` (spec-096)
 * onto the cockpit's Cold Collapse palette tokens. Lazily mounted via
 * `ObservatoryRoute` so it adds no weight to the main game bundle.
 */

import { useEffect, useState } from "react";
import { fetchSessions, fetchStatus } from "./api";
import { DeepPanes } from "./DeepPanes";
import type { Source } from "./deepApi";
import { SessionPicker } from "./SessionPicker";
import { SeriesBrowser } from "./SeriesBrowser";
import type { ObservatorySession } from "./types";

type LoadState = "checking" | "unavailable" | "ready";
type DetailView = "series" | "diagnostics";
const SOURCES: Source[] = ["live", "archive"];

export default function ObservatoryPage() {
  const [loadState, setLoadState] = useState<LoadState>("checking");
  const [source, setSource] = useState<Source>("live");
  const [sessions, setSessions] = useState<ObservatorySession[]>([]);
  const [selected, setSelected] = useState<ObservatorySession | null>(null);
  const [detail, setDetail] = useState<DetailView>("series");

  useEffect(() => {
    let active = true;
    void (async () => {
      const status = await fetchStatus();
      if (!active) return;
      if (status === null || !status.enabled) {
        setLoadState("unavailable");
        return;
      }
      const list = await fetchSessions(source);
      if (!active) return;
      setSessions(list);
      setSelected(null);
      setLoadState("ready");
    })();
    return () => {
      active = false;
    };
  }, [source]);

  return (
    <div className="flex h-screen w-screen flex-col bg-void text-bone">
      <header className="flex shrink-0 items-center justify-between border-b border-rebar bg-concrete px-6 py-4">
        <div>
          <h1 className="text-lg font-bold tracking-widest text-spire">OBSERVATORY</h1>
          <p className="mt-0.5 text-xs text-ash">
            Read-only debug dashboard over the simulation database
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-ash">
          source
          <select
            aria-label="source"
            value={source}
            onChange={(e) => setSource(e.target.value as Source)}
            className="rounded border border-rebar bg-void px-2 py-1 text-xs text-bone"
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
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
            <code className="text-fog">OBSERVATORY_ENABLED</code>) and requires the simulation
            database.
          </div>
        )}

        {loadState === "ready" && selected === null && (
          <SessionPicker sessions={sessions} onSelect={setSelected} />
        )}

        {loadState === "ready" && selected !== null && (
          <div className="flex h-full flex-col">
            <div className="flex shrink-0 items-center gap-2 border-b border-rebar px-4 py-2">
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="text-xs text-fog hover:text-spire"
              >
                ← sessions
              </button>
              {(["series", "diagnostics"] as DetailView[]).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDetail(d)}
                  className={`rounded px-2 py-0.5 text-[11px] uppercase tracking-wider ${
                    detail === d ? "bg-rebar text-spire" : "text-ash hover:text-fog"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
            <div className="min-h-0 flex-1">
              {detail === "series" ? (
                <SeriesBrowser session={selected} source={source} />
              ) : (
                <DeepPanes sessionId={selected.session_id} source={source} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
