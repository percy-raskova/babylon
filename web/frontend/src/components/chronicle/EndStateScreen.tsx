/**
 * EndStateScreen - chronicle end-screen for terminal outcomes.
 * Spec 095 FR-095-09: ports EndState.jsx as fresh TypeScript.
 *
 * The `outcome` prop drives the palette (rupture = bronze-gold, defeat =
 * laser-red) and headline. REVOLUTIONARY_VICTORY → "BABYLON FALLS"; all
 * others → "THE BUNKER FAILS". Fed by useEndgame hook polling
 * GET /api/games/:id/endgame/.
 *
 * Constitution III: pure read.
 */

import { useEndgame } from "@/hooks/useEndgame";
import type { EndgameState } from "@/types/dialectic";
import "@/components/chronicle/chronicle.css";

interface Props {
  gameId: string;
  onRestart?: () => void;
}

/** Stat card descriptor — drives the 4-card row. */
interface StatCard {
  label: string;
  value: string;
  color: string;
}

function buildStats(state: EndgameState): StatCard[] {
  const tick = String(state.stats.final_tick).padStart(4, "0");
  return [
    { label: "Final Tick", value: tick, color: "var(--babylon-spire)" },
    {
      label: "Consciousness",
      value: state.stats.consciousness.toFixed(2),
      color: "var(--babylon-cadre)",
    },
    {
      label: "Solidarity Edges",
      value: String(state.stats.solidarity_edges),
      color: "var(--babylon-solidarity)",
    },
    {
      label: "Heat at End",
      value: state.stats.heat.toFixed(2),
      color: "var(--babylon-heat)",
    },
  ];
}

export function EndStateScreen({ gameId, onRestart }: Props) {
  const { data: state, loading, error } = useEndgame(gameId);

  const isRupture = state.outcome === "revolutionary_victory";
  let palette: string;
  if (state.outcome) {
    palette = isRupture ? "end-state--rupture" : "end-state--defeat";
  } else {
    palette = "end-state--pending";
  }

  if (!state.outcome) {
    let pendingText: string;
    if (loading) {
      pendingText = "Reading terminal state…";
    } else if (error) {
      pendingText = `Error: ${error}`;
    } else {
      pendingText = "Operation in progress — no terminal outcome yet.";
    }
    return (
      <div className={`end-state ${palette}`}>
        <div className="end-state-scanlines" />
        <div className="end-state-content">
          <div className="end-state-pending-text">{pendingText}</div>
        </div>
      </div>
    );
  }

  const stats = buildStats(state);
  const kicker = isRupture ? "▸ Rupture Achieved" : "✕ Organizational Collapse";

  return (
    <div className={`end-state ${palette}`}>
      <div className="end-state-scanlines" />
      <div className="end-state-content">
        <div className="end-state-kicker">{kicker}</div>
        <h1 className="end-state-headline">{state.headline}</h1>
        {state.summary && <p className="end-state-summary">{state.summary}</p>}
        <div className="end-state-stats">
          {stats.map((s) => (
            <div key={s.label} className="end-state-stat">
              <div className="end-state-stat-label">{s.label}</div>
              <div className="end-state-stat-value" style={{ color: s.color }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>
        {onRestart && (
          <button className="end-state-restart" onClick={onRestart}>
            ▸ New Operation
          </button>
        )}
      </div>
    </div>
  );
}
