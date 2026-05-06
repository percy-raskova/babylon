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
 */

import { BblData, BblLabel, BblBadge, Gauge } from "@/components/bbl";
import { TICK, SCENARIO, ORGS } from "@/fixtures/v2-mock-data";

interface TopBarV2Props {
  username: string;
  onBack: () => void;
  onLogout: () => void;
}

export function TopBarV2({ username, onBack, onLogout }: TopBarV2Props) {
  // Use first player org for vanguard readouts (will be store-driven later)
  const playerOrg = ORGS.find((o) => o.player_controlled);
  const v = playerOrg?.vanguard;

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
          <span className="text-[9px] tracking-[0.15em] text-ash">{SCENARIO.name}</span>
        </div>
      </div>

      {/* Center: Tick + OODA */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <BblLabel>Tick</BblLabel>
          <BblData color="#c8a860" size={16}>
            {TICK}
          </BblData>
        </div>
        {playerOrg && <BblBadge color="#80b0e0">{playerOrg.ooda_phase}</BblBadge>}
      </div>

      {/* Right-center: Vanguard gauges */}
      {v && (
        <div className="flex items-center gap-3">
          <Gauge label="CL" value={v.cl} max={v.cl_max} color="#80b0e0" tooltip="Cadre Labor" />
          <Gauge
            label="SL"
            value={v.sl}
            max={v.sl_max}
            color="#40c040"
            tooltip="Sympathizer Labor"
          />
          <div className="flex flex-col gap-0.5">
            <div className="flex items-baseline gap-1">
              <BblLabel>REP</BblLabel>
              <BblData size={10}>{(v.rep * 100).toFixed(0)}%</BblData>
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
