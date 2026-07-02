/**
 * TopBarV2 — v2 top bar with brand block, tick display, vanguard readouts.
 *
 * Simplified compared to v1: no lens bar, no inline sparklines.
 * Those are now per-page concerns. TopBar focuses on:
 *   - Brand (BABYLON + scenario subtitle)
 *   - Tick + OODA phase
 *   - Vanguard resource gauges (CL, SL, REP, $, HEAT)
 *   - RESOLVE TICK button
 *   - User/logout
 *
 * Live-data migration (spec 061 US6 pattern, matching ResultsPage T102):
 * reads the session snapshot via useGameState instead of the v2-mock-data
 * fixtures. Rendered inside the `/game/:id` route (GameRouteShell), so
 * useParams resolves the session id directly.
 */

import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { get } from "@/api/client";
import { BblData, BblLabel, BblBadge, Gauge } from "@/components/bbl";
import { useGameState } from "@/hooks/useGameState";
import type { GameSummary } from "@/types/game";

interface TopBarV2Props {
  username: string;
  onBack: () => void;
  onLogout: () => void;
}

export function TopBarV2({ username, onBack, onLogout }: TopBarV2Props) {
  const { id: gameId } = useParams<{ id: string }>();
  const { snapshot } = useGameState(gameId ?? null);

  // Scenario lives on the session record, not the snapshot; fetched once
  // per shell mount (GameRouteShell persists across in-game routes).
  const [scenario, setScenario] = useState<string>("—");
  useEffect(() => {
    if (!gameId) return;
    let cancelled = false;
    get<GameSummary[]>("/api/games/")
      .then((res) => {
        if (cancelled || res.status !== "ok") return;
        const game = res.data.find((g) => g.id === gameId);
        if (game) setScenario(game.scenario);
      })
      .catch(() => undefined); // subtitle is cosmetic; never block the shell
    return () => {
      cancelled = true;
    };
  }, [gameId]);

  const tick = snapshot?.tick ?? 0;
  const playerOrg = snapshot?.organizations?.find((o) => Boolean(o.player_controlled));
  const v = playerOrg?.vanguard ?? null;

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-soot bg-void px-3 py-1.5">
      {/* Left: Brand + back */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-xs text-ash transition-colors hover:text-gold"
          aria-label="Back to games"
        >
          ←
        </button>
        <div className="flex flex-col">
          <span className="text-sm font-bold tracking-[0.25em] text-gold bloom-gold">BABYLON</span>
          <span className="text-[9px] tracking-[0.15em] text-ash">{scenario}</span>
        </div>
      </div>

      {/* Center: Tick + OODA */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <BblLabel>Tick</BblLabel>
          <BblData color="#c8a860" size={16}>
            {tick}
          </BblData>
        </div>
        {playerOrg?.ooda?.phase && <BblBadge color="#80b0e0">{playerOrg.ooda.phase}</BblBadge>}
      </div>

      {/* Right-center: Vanguard gauges */}
      {v && (
        <div className="flex items-center gap-3">
          <Gauge
            label="CL"
            value={v.cadre_labor}
            max={v.max_cadre_labor}
            color="#80b0e0"
            tooltip="Cadre Labor"
          />
          <Gauge
            label="SL"
            value={v.sympathizer_labor}
            max={v.max_sympathizer_labor}
            color="#40c040"
            tooltip="Sympathizer Labor"
          />
          <div className="flex flex-col gap-0.5">
            <div className="flex items-baseline gap-1">
              <BblLabel>REP</BblLabel>
              <BblData size={10}>{(v.reputation * 100).toFixed(0)}%</BblData>
            </div>
            <div className="flex items-baseline gap-1">
              <BblLabel>$</BblLabel>
              <BblData size={10} color="#c8a860">
                {v.budget}
              </BblData>
            </div>
          </div>
          <div className="flex flex-col gap-0.5">
            <div className="flex items-baseline gap-1">
              <BblLabel color="#e04040">HEAT</BblLabel>
              <BblData size={10} color="#e04040">
                {(v.heat * 100).toFixed(0)}%
              </BblData>
            </div>
          </div>
        </div>
      )}

      {/* Right: Resolve + User */}
      <div className="flex items-center gap-3">
        <button
          className="rounded-md bg-gold px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.2em] text-void transition-all hover:brightness-110"
          data-testid="resolve-tick-btn"
        >
          Resolve Tick ▸
        </button>
        <div className="flex items-center gap-2 border-l border-soot pl-3">
          <span className="text-[11px] text-silver">{username}</span>
          <button
            onClick={onLogout}
            className="text-[10px] text-ash transition-colors hover:text-crimson"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
