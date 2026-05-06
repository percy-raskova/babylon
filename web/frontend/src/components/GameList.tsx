/**
 * Game list / lobby — v2 restyled.
 *
 * Shows the player's games and allows creating new ones with scenario selection.
 * Uses Bunker Constructivism panel layout with v2 primitives.
 */

import { useEffect, useState } from "react";
import { get, post } from "@/api/client";
import { BblPanel, BblBadge, BblLabel, BblData } from "@/components/bbl";
import type { GameSummary, CreateGameParams } from "@/types/game";

/** Scenario metadata from GET /api/scenarios/. */
interface ScenarioInfo {
  key: string;
  name: string;
  description: string;
  territory_count: number;
}

interface GameListProps {
  onSelectGame: (gameId: string) => void;
}

export function GameList({ onSelectGame }: GameListProps) {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>("us_nationwide");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      const [gamesRes, scenariosRes] = await Promise.all([
        get<GameSummary[]>("/api/games/"),
        get<ScenarioInfo[]>("/api/scenarios/"),
      ]);
      if (cancelled) return;
      if (gamesRes.status === "ok") {
        setGames(gamesRes.data);
      } else {
        setError(gamesRes.message ?? "Failed to load games");
      }
      if (scenariosRes.status === "ok") {
        setScenarios(scenariosRes.data);
        if (scenariosRes.data.length > 0 && scenariosRes.data[0]) {
          setSelectedScenario(scenariosRes.data[0].key);
        }
      }
      if (!cancelled) {
        setLoading(false);
      }
    }
    void fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    const params: CreateGameParams = { scenario: selectedScenario };
    const res = await post<{ session_id: string }>("/api/games/", params);
    setCreating(false);

    if (res.status === "ok") {
      onSelectGame(res.data.session_id);
    } else {
      setError(res.message ?? "Failed to create game");
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center text-sm text-ash">
        Loading games...
      </div>
    );
  }

  const selectedInfo = scenarios.find((s) => s.key === selectedScenario);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-void">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-6 py-8">
        {/* Create new game */}
        <BblPanel
          title="New Operation"
          accent="#c8a860"
          right={
            <div className="flex items-center gap-2">
              {scenarios.length > 1 && (
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  className="rounded border border-soot bg-void px-2 py-1.5 text-[11px] text-bone focus:border-gold focus:outline-none"
                >
                  {scenarios.map((s) => (
                    <option key={s.key} value={s.key}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
              <button
                onClick={handleCreate}
                disabled={creating}
                className="rounded-md bg-gold px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] text-void transition-all hover:brightness-110 disabled:opacity-50"
              >
                {creating ? "Creating..." : "+ New Game"}
              </button>
            </div>
          }
        >
          {selectedInfo ? (
            <div className="flex items-start gap-4">
              <div className="flex-1">
                <div className="text-[12px] text-bone">{selectedInfo.description}</div>
                <div className="mt-1 flex gap-3 text-[10px]">
                  <span className="text-ash">{selectedInfo.territory_count} territories</span>
                  <span className="text-chassis">·</span>
                  <span className="text-ash">scenario: {selectedInfo.key}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-ash">Select a scenario above</div>
          )}
        </BblPanel>

        {error && <p className="text-[12px] text-crimson">{error}</p>}

        {/* Game list */}
        <BblPanel
          title="Your Operations"
          right={<BblBadge color="#787878">{games.length}</BblBadge>}
        >
          {games.length === 0 ? (
            <div className="py-12 text-center text-[13px] text-ash">
              No operations yet. Create one to begin organizing.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {games.map((game) => (
                <button
                  key={game.id}
                  onClick={() => onSelectGame(game.id)}
                  className="flex w-full items-center justify-between rounded-lg border border-soot bg-void px-4 py-3.5 text-left transition-colors hover:border-gold"
                >
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-semibold text-bone">{game.scenario}</span>
                      <BblBadge color={game.status === "active" ? "#40c040" : "#787878"}>
                        {game.status}
                      </BblBadge>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-ash">
                      <BblLabel>Tick</BblLabel>
                      <BblData color="#c8a860" size={11}>
                        {game.current_tick}
                      </BblData>
                    </div>
                  </div>
                  <div className="font-mono text-[10px] text-chassis">{game.id.slice(0, 8)}…</div>
                </button>
              ))}
            </div>
          )}
        </BblPanel>
      </div>
    </div>
  );
}
