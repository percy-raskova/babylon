/**
 * EndStateScreen - chronicle end-screen for terminal outcomes.
 * Spec 095 FR-095-09 + spec-116 FR-116-4.2 (six distinct epilogues).
 *
 * The backend payload drives everything: `headline`/`epilogue` come from
 * web/game/epilogues.py (one distinct text per GameOutcome incl.
 * "unresolved"), `palette` picks one of three palette families (rupture
 * bronze-gold / defeat laser-red / unresolved spire-cyan), and
 * `accepted_at_tick` frames a player-accepted fast-forward (FR-116-5).
 * Fed by useEndgame polling GET /api/games/:id/endgame/.
 *
 * The deterministic epilogue is rendered separately from the "Last
 * Dispatch" epitaph (the flag-off LLM narration channel) — deterministic
 * copy must never masquerade as AI narration.
 *
 * Constitution III: pure read.
 */

import { useEndgame } from "@/hooks/useEndgame";
import { useNarration } from "@/hooks/useNarration";
import { NarrationBlock } from "@/components/narration/NarrationBlock";
import type { EndgameState } from "@/types/dialectic";
import "@/components/takeovers/chronicle/chronicle.css";

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

/** Palette-keyed kickers — the one-line framing above the headline. */
const KICKERS: Record<"rupture" | "defeat" | "unresolved", string> = {
  rupture: "▸ Rupture Achieved",
  defeat: "✕ Organizational Collapse",
  unresolved: "◌ Horizon Reached — The Struggle Continues",
};

export function EndStateScreen({ gameId, onRestart }: Props) {
  const { data: state, loading, error } = useEndgame(gameId);
  const { status: narrationStatus, beats } = useNarration(gameId);
  const endgameBeat = beats.filter((b) => b.scope === "endgame").at(-1) ?? null;

  const isRupture = state.outcome === "revolutionary_victory";
  let palette: string;
  if (!state.outcome) {
    palette = "end-state--pending";
  } else if (state.palette !== "") {
    palette = `end-state--${state.palette}`;
  } else {
    // Defensive fallback for a payload predating spec-116.
    palette = isRupture ? "end-state--rupture" : "end-state--defeat";
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
      <div className={`end-state ${palette}`} data-testid="end-state" data-outcome="pending">
        <div className="end-state-scanlines" />
        <div className="end-state-content">
          <div className="end-state-pending-text">{pendingText}</div>
        </div>
      </div>
    );
  }

  const stats = buildStats(state);
  let kicker: string;
  if (state.palette !== "") {
    kicker = KICKERS[state.palette];
  } else {
    kicker = isRupture ? KICKERS.rupture : KICKERS.defeat;
  }

  return (
    <div className={`end-state ${palette}`} data-testid="end-state" data-outcome={state.outcome}>
      <div className="end-state-scanlines" />
      <div className="end-state-content">
        <div className="end-state-kicker">{kicker}</div>
        <h1 className="end-state-headline">{state.headline}</h1>
        {state.accepted_at_tick !== null && (
          <div className="end-state-accepted" data-testid="end-state-accepted">
            ▸ Outcome accepted at tick {state.accepted_at_tick} — fast-forwarded to the epilogue.
          </div>
        )}
        {/* Deterministic epilogue (spec-116 FR-116-4.2). The wire `summary`
            field is degraded machine text ("Endgame Reached") — superseded
            here, still on the wire for contract compat. */}
        {state.epilogue && <p className="end-state-epilogue-body">{state.epilogue}</p>}
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
        {/* Epitaph — the narrator's last word on this operation. Endgames are
            never neutral scoreboard text (Design Bible §7); honest
            offline/pending states render via NarrationBlock, never blank. */}
        <div className="end-state-epitaph">
          <div className="end-state-epitaph-label">Last Dispatch</div>
          <NarrationBlock beat={endgameBeat} state={narrationStatus} />
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
