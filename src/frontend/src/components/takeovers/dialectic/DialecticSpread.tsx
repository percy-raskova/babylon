/**
 * DialecticSpread - card grid of active contradictions.
 * Spec 095 FR-095-08: ports DialecticSpread.jsx as fresh TypeScript.
 *
 * Each card shows thesis <-> antithesis, tension bar, rate, regime.
 * Principal contradiction is highlighted. Fed by useContradiction hook
 * polling GET /api/games/:id/contradiction/.
 *
 * Constitution III: pure read — surfaces contradiction state the engine's
 * ContradictionSystem already computed. Never computes dialectical state.
 */

import { useContradiction } from "@/hooks/useContradiction";
import type { ContradictionSnapshot, OppositionEntry } from "@/types/dialectic";
import "@/components/takeovers/dialectic/dialectic.css";

interface Props {
  gameId: string;
}

/** Map a regime to its canonical Cold Collapse accent color. */
function regimeColor(regime: string): string {
  switch (regime) {
    case "sublation":
      return "var(--babylon-rupture)";
    case "crisis":
      return "var(--babylon-laser)";
    default:
      return "var(--babylon-cadre)";
  }
}

/** Resolve the thesis/antithesis labels for an opposition from the frame. */
function poleLabels(
  opp: OppositionEntry,
  snapshot: ContradictionSnapshot,
): { thesis: string; antithesis: string } {
  const frame = snapshot.frame;
  let aspect;
  if (opp.key === frame.principal.id) {
    aspect = frame.principal;
  } else if (opp.key === frame.secondary.id) {
    aspect = frame.secondary;
  } else {
    aspect = null;
  }
  if (aspect) {
    return { thesis: aspect.aspect_a, antithesis: aspect.aspect_b };
  }
  return { thesis: opp.key, antithesis: opp.leading_pole || "—" };
}

export function DialecticSpread({ gameId }: Props) {
  const { data: snapshot, loading, error } = useContradiction(gameId);

  const accent = regimeColor(snapshot.regime);

  return (
    <div className="dialectic-spread">
      <div className="dialectic-header">
        <span className="dialectic-regime-badge" style={{ color: accent, borderColor: accent }}>
          {snapshot.regime}
        </span>
        <div className="dialectic-title">▸ Active Contradictions</div>
        <div className="dialectic-count">{snapshot.oppositions.length} active</div>
      </div>

      {loading && snapshot.oppositions.length === 0 && (
        <div className="dialectic-empty">Loading contradiction layer…</div>
      )}
      {error && <div className="dialectic-empty">Error: {error}</div>}

      {snapshot.oppositions.length === 0 && !loading && !error && (
        <div className="dialectic-empty">No oppositions registered.</div>
      )}

      <div className="dialectic-grid">
        {snapshot.oppositions.map((opp, i) => {
          const isPrincipal = opp.is_principal || opp.key === snapshot.principal_key;
          const color = regimeColor(snapshot.regime);
          const { thesis, antithesis } = poleLabels(opp, snapshot);
          const tensionPct = `${Math.min(100, Math.max(0, opp.gap * 100)).toFixed(0)}%`;
          const num = String(i + 1).padStart(2, "0");

          return (
            <div
              key={opp.key || num}
              className={`dialectic-card${isPrincipal ? " dialectic-card--principal" : ""}`}
            >
              <div
                className="dialectic-card-glow"
                style={{
                  background: `radial-gradient(ellipse at top right, ${color}, transparent 60%)`,
                }}
              />
              <div className="dialectic-card-body">
                <div className="dialectic-card-label" style={{ color }}>
                  ● Contradiction {num}
                  {isPrincipal ? " · PRINCIPAL" : ""}
                </div>
                <div className="dialectic-poles">
                  <div style={{ textAlign: "right" }}>
                    <div className="dialectic-pole-label">Thesis</div>
                    <div className="dialectic-pole-value">{thesis}</div>
                  </div>
                  <div className="dialectic-glyph" style={{ color }}>
                    ↮
                  </div>
                  <div>
                    <div className="dialectic-pole-label">Antithesis</div>
                    <div className="dialectic-pole-value">{antithesis}</div>
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div className="dialectic-tension-row">
                    <span className="dialectic-tension-label">Tension</span>
                    <span className="dialectic-tension-value" style={{ color }}>
                      {opp.gap.toFixed(2)}
                    </span>
                  </div>
                  <div className="dialectic-tension-track">
                    <div
                      className="dialectic-tension-fill"
                      style={{
                        width: tensionPct,
                        background: color,
                        boxShadow: `0 0 8px ${color}`,
                      }}
                    />
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div className="dialectic-tension-row">
                    <span className="dialectic-tension-label">Rate</span>
                    <span className="dialectic-tension-value" style={{ color }}>
                      {opp.rate >= 0 ? "+" : ""}
                      {opp.rate.toFixed(3)}
                    </span>
                  </div>
                </div>
                <div className="dialectic-synthesis">
                  <span className="dialectic-synthesis-label">Synthesis</span>
                  <span className="dialectic-synthesis-value" style={{ color }}>
                    ▸ {snapshot.regime}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
