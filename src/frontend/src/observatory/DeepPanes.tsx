/**
 * Observatory deep panes (spec-099): hash-chain verification, boundary-flow
 * explorer (empty-state-first), and conservation-audit browser. Source-aware
 * (live|archive). Tufte-minimal, palette tokens.
 *
 * Ported from `web/frontend/src/observatory/DeepPanes.tsx` onto the
 * cockpit's Cold Collapse palette (spec-090): `crimson`→`laser` (alarm),
 * `warning-amber`→`heat` (warn), `data-green`→`solidarity` (ok/valid),
 * `gold`→`spire` (active tab — headings/actives use spire, not gold, per
 * `src/index.css`'s semantic-type-role note), `soot`→`rebar`, `silver`→`fog`.
 */

import { useEffect, useState } from "react";
import {
  fetchBoundary,
  fetchConservation,
  fetchVerify,
  type BoundaryResult,
  type ConservationResult,
  type Source,
  type VerifyResult,
} from "./deepApi";

type DeepTab = "verify" | "boundary" | "conservation";
const TABS: DeepTab[] = ["verify", "boundary", "conservation"];

interface DeepPanesProps {
  sessionId: string;
  source: Source;
}

/** ``loading`` until the first fetch settles; then ``ready`` carrying data. */
type Loadable<T> = { status: "loading" } | { status: "ready"; data: T };

export function DeepPanes({ sessionId, source }: DeepPanesProps) {
  const [tab, setTab] = useState<DeepTab>("verify");
  return (
    <div className="flex h-full flex-col gap-2 p-4" data-testid="deep-panes">
      <div className="flex gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded px-2 py-0.5 text-[11px] uppercase tracking-wider ${
              tab === t ? "bg-rebar text-spire" : "text-ash hover:text-fog"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {tab === "verify" && <VerificationPane sessionId={sessionId} source={source} />}
        {tab === "boundary" && <BoundaryPane sessionId={sessionId} source={source} />}
        {tab === "conservation" && <ConservationPane sessionId={sessionId} source={source} />}
      </div>
    </div>
  );
}

export function VerificationPane({ sessionId, source }: DeepPanesProps) {
  const [state, setState] = useState<Loadable<VerifyResult | null>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    async function load() {
      const result = await fetchVerify(sessionId, source);
      if (active) {
        setState({ status: "ready", data: result });
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [sessionId, source]);

  if (state.status === "loading") {
    return (
      <div role="status" className="text-sm text-ash">
        Verifying…
      </div>
    );
  }
  const result = state.data;
  if (result === null) {
    return (
      <div role="alert" className="text-sm text-ash">
        Verification unavailable
      </div>
    );
  }
  return (
    <div data-testid="verify-pane" className="flex flex-col gap-2 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`rounded px-2 py-0.5 text-xs font-bold ${
            result.valid ? "bg-rebar text-solidarity" : "bg-rebar text-laser"
          }`}
        >
          {result.valid ? "STRUCTURE OK" : "STRUCTURE ANOMALY"}
        </span>
        <span className="text-ash">
          ticks {result.min_tick ?? "—"}–{result.max_tick ?? "—"} · {result.tick_count} committed ·{" "}
          {result.checkpoint_ticks.length} checkpoints
        </span>
      </div>
      <p className="text-[11px] text-ash" data-testid="verify-scope-note">
        Checks tick contiguity, checkpoint cadence, and hash FORMAT (length) only — NOT
        content/tamper verification of the hash itself.
      </p>
      {result.anomalies.length > 0 && (
        <ul className="flex flex-col gap-0.5 font-mono text-xs text-laser" data-testid="anomalies">
          {result.anomalies.map((a) => (
            <li key={`${a.kind}-${a.tick}`}>
              t{a.tick} · {a.kind}: {a.detail}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function BoundaryPane({ sessionId, source }: DeepPanesProps) {
  const [state, setState] = useState<Loadable<BoundaryResult | null>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    async function load() {
      const result = await fetchBoundary(sessionId, source);
      if (active) {
        setState({ status: "ready", data: result });
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [sessionId, source]);

  if (state.status === "loading") {
    return (
      <div role="status" className="text-sm text-ash">
        Loading…
      </div>
    );
  }
  const result = state.data;
  if (result === null || result.by_flow_type.length === 0) {
    return (
      <div role="status" className="text-sm text-ash" data-testid="boundary-empty">
        No cross-boundary flows recorded (trade activates in a later spec).
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {result.truncated && (
        <div role="status" className="text-xs font-bold text-heat" data-testid="boundary-truncated">
          Results truncated at {result.rows.length} rows — narrow the tick range to see more.
        </div>
      )}
      <table className="w-full text-left text-xs" data-testid="boundary-table">
        <thead className="text-ash">
          <tr>
            <th className="py-1">flow type</th>
            <th>rows</th>
            <th>total magnitude</th>
          </tr>
        </thead>
        <tbody className="font-mono text-bone">
          {result.by_flow_type.map((f) => (
            <tr key={f.flow_type} className="border-t border-rebar">
              <td className="py-1">{f.flow_type}</td>
              <td>{f.row_count}</td>
              <td>{f.total_magnitude.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const SEVERITY_COLOR: Record<string, string> = {
  ok: "text-ash",
  warn: "text-heat",
  alarm: "text-laser",
};

export function ConservationPane({ sessionId, source }: DeepPanesProps) {
  const [state, setState] = useState<Loadable<ConservationResult>>({ status: "loading" });
  const [nonOkOnly, setNonOkOnly] = useState(false);
  useEffect(() => {
    let active = true;
    async function load() {
      const result = await fetchConservation(sessionId, source, nonOkOnly);
      if (active) {
        setState({ status: "ready", data: result });
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [sessionId, source, nonOkOnly]);

  return (
    <div className="flex flex-col gap-2">
      <label className="flex items-center gap-1 text-xs text-ash">
        <input
          type="checkbox"
          checked={nonOkOnly}
          onChange={(e) => setNonOkOnly(e.target.checked)}
        />
        warn/alarm only
      </label>
      {state.status === "loading" && (
        <div role="status" className="text-sm text-ash">
          Loading…
        </div>
      )}
      {state.status === "ready" && state.data.rows.length === 0 && (
        <div role="status" className="text-sm text-ash" data-testid="conservation-empty">
          No conservation-audit rows.
        </div>
      )}
      {state.status === "ready" && state.data.rows.length > 0 && (
        <>
          {state.data.truncated && (
            <div
              role="status"
              className="text-xs font-bold text-heat"
              data-testid="conservation-truncated"
            >
              Results truncated at {state.data.rows.length} rows — narrow the tick range or filter
              to warn/alarm only.
            </div>
          )}
          <table className="w-full text-left text-xs" data-testid="conservation-table">
            <thead className="text-ash">
              <tr>
                <th className="py-1">tick</th>
                <th>scale</th>
                <th>invariant</th>
                <th>residual</th>
                <th>severity</th>
              </tr>
            </thead>
            <tbody className="font-mono text-bone">
              {state.data.rows.map((r) => (
                <tr
                  key={`${r.tick}-${r.scale}-${r.invariant_name}`}
                  className="border-t border-rebar"
                >
                  <td className="py-1">{r.tick}</td>
                  <td>{r.scale}</td>
                  <td>{r.invariant_name}</td>
                  <td>{r.residual.toFixed(4)}</td>
                  <td className={SEVERITY_COLOR[r.severity] ?? "text-bone"}>{r.severity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
