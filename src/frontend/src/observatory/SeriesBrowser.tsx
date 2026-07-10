/**
 * Series browser — pick scope + metrics, plot the value-aggregate series for a
 * session, and export the underlying numbers as CSV.
 *
 * Ported from `web/frontend/src/observatory/SeriesBrowser.tsx` (spec-096)
 * onto the cockpit's Cold Collapse palette tokens.
 */

import { useEffect, useState } from "react";
import { fetchSeries } from "./api";
import { downloadCsv, seriesToCsv } from "./csv";
import { METRIC_LABELS, ObservatoryChart } from "./ObservatoryChart";
import {
  SERIES_METRICS,
  type ObservatorySession,
  type Scope,
  type Series,
  type SeriesMetric,
} from "./types";

const SCOPES: Scope[] = ["national", "state", "county"];
const SCOPE_ID_LEN: Record<Scope, number> = { national: 0, state: 2, county: 5 };

interface SeriesBrowserProps {
  session: ObservatorySession;
  source?: "live" | "archive";
}

export function SeriesBrowser({ session, source = "live" }: SeriesBrowserProps) {
  const [scope, setScope] = useState<Scope>("national");
  const [scopeId, setScopeId] = useState("");
  const [metrics, setMetrics] = useState<SeriesMetric[]>(["v_sum", "s_sum"]);
  const [series, setSeries] = useState<Series | null>(null);

  const scopeReady = scope === "national" || scopeId.length === SCOPE_ID_LEN[scope];
  const wantedScopeId = scope === "national" ? "USA" : scopeId;
  // Derived "loading": the loaded series does not yet match the requested scope.
  const matched = series !== null && series.scope === scope && series.scope_id === wantedScopeId;

  useEffect(() => {
    if (!scopeReady) {
      return;
    }
    let cancelled = false;
    async function load() {
      const result = await fetchSeries(session.session_id, scope, scopeId, { source });
      if (!cancelled) {
        setSeries(result);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [session.session_id, scope, scopeId, scopeReady, source]);

  const toggleMetric = (metric: SeriesMetric) =>
    setMetrics((current) =>
      current.includes(metric) ? current.filter((m) => m !== metric) : [...current, metric],
    );

  const exportCsv = () => {
    if (!series) return;
    downloadCsv(`${session.session_id}_${scope}_${wantedScopeId}.csv`, seriesToCsv(series.points));
  };

  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <span className="font-mono text-xs text-ash">{session.session_id}</span>

      <div className="flex flex-wrap items-center gap-3">
        <select
          aria-label="scope"
          value={scope}
          onChange={(e) => setScope(e.target.value as Scope)}
          className="rounded border border-rebar bg-void px-2 py-1 text-xs text-bone"
        >
          {SCOPES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        {scope !== "national" && (
          <input
            aria-label="scope id"
            value={scopeId}
            placeholder={scope === "state" ? "state FIPS (26)" : "county FIPS (26163)"}
            onChange={(e) => setScopeId(e.target.value.replace(/\D/g, ""))}
            maxLength={SCOPE_ID_LEN[scope]}
            className="w-40 rounded border border-rebar bg-void px-2 py-1 text-xs text-bone"
          />
        )}
        <div className="flex flex-wrap gap-1">
          {SERIES_METRICS.map((metric) => (
            <button
              key={metric}
              type="button"
              onClick={() => toggleMetric(metric)}
              className={`rounded px-2 py-0.5 text-[10px] uppercase tracking-wider ${
                metrics.includes(metric) ? "bg-rebar text-spire" : "text-ash hover:text-fog"
              }`}
            >
              {METRIC_LABELS[metric]}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={exportCsv}
          disabled={!series || series.points.length === 0}
          className="ml-auto rounded border border-wet-steel px-3 py-1 text-xs text-fog hover:border-fog disabled:opacity-40"
        >
          Export CSV
        </button>
      </div>

      <div className="min-h-0 flex-1">
        {!scopeReady && (
          <div role="status" className="flex h-full items-center justify-center text-sm text-ash">
            Enter a {scope} FIPS to load the series
          </div>
        )}
        {scopeReady && !matched && (
          <div role="status" className="flex h-full items-center justify-center text-sm text-ash">
            Loading…
          </div>
        )}
        {scopeReady && matched && series !== null && (
          <ObservatoryChart points={series.points} metrics={metrics} />
        )}
      </div>
    </div>
  );
}
