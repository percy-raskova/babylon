/**
 * Game list component.
 *
 * Shows the player's games and allows creating new ones with scenario selection.
 */

import { useEffect, useState } from "react";
import { get, post } from "@/api/client";
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
    return <div className="p-16 text-center text-silver">Loading games...</div>;
  }

  const selectedInfo = scenarios.find((s) => s.key === selectedScenario);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-bone">Your Games</h2>
        <div className="flex items-center gap-3">
          {scenarios.length > 1 && (
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="rounded border border-soot bg-void px-2 py-2 text-[12px] text-bone focus:border-gold focus:outline-none"
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
            className="rounded-lg bg-gold px-5 py-2.5 text-sm font-semibold text-void hover:brightness-110 disabled:opacity-50"
          >
            {creating ? "Creating..." : "+ New Game"}
          </button>
        </div>
      </div>

      {selectedInfo && (
        <p className="mb-4 text-[12px] text-ash">
          {selectedInfo.description} ({selectedInfo.territory_count} territories)
        </p>
      )}

      {error && <p className="mb-4 text-[13px] text-crimson">{error}</p>}

      {games.length === 0 ? (
        <p className="py-12 text-center text-[15px] text-ash">No games yet. Create one to begin.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {games.map((game) => (
            <button
              key={game.id}
              onClick={() => onSelectGame(game.id)}
              className="w-full rounded-lg border border-wet-concrete bg-dark-metal px-5 py-4 text-left text-sm text-bone hover:border-gold"
            >
              <div className="mb-2 flex justify-between">
                <span className="text-base font-semibold">{game.scenario}</span>
                <span
                  className={`text-[13px] uppercase tracking-wider ${
                    game.status === "active" ? "text-data-green" : "text-silver"
                  }`}
                >
                  {game.status}
                </span>
              </div>
              <div className="flex justify-between text-[13px] text-silver">
                <span>Tick {game.current_tick}</span>
                <span className="font-mono">{game.id.slice(0, 8)}...</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
