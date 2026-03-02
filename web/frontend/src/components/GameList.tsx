/**
 * Game list component.
 *
 * Shows the player's games and allows creating new ones.
 */

import { useCallback, useEffect, useState } from "react";
import { get, post } from "@/api/client";
import type { GameSummary, CreateGameParams } from "@/types/game";

interface GameListProps {
  onSelectGame: (gameId: string) => void;
}

export function GameList({ onSelectGame }: GameListProps) {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGames = useCallback(async () => {
    setLoading(true);
    const res = await get<GameSummary[]>("/api/games/");
    if (res.status === "ok") {
      setGames(res.data);
    } else {
      setError(res.message ?? "Failed to load games");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void fetchGames();
  }, [fetchGames]);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    const params: CreateGameParams = { scenario: "default" };
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
      <div className="p-16 text-center text-silver">Loading games...</div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-bone">Your Games</h2>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="rounded-lg bg-gold px-5 py-2.5 text-sm font-semibold text-void hover:brightness-110 disabled:opacity-50"
        >
          {creating ? "Creating..." : "+ New Game"}
        </button>
      </div>

      {error && <p className="mb-4 text-[13px] text-crimson">{error}</p>}

      {games.length === 0 ? (
        <p className="py-12 text-center text-[15px] text-ash">
          No games yet. Create one to begin.
        </p>
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
