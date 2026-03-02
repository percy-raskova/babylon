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
    return <div style={styles.loading}>Loading games...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Your Games</h2>
        <button
          onClick={handleCreate}
          disabled={creating}
          style={styles.createButton}
        >
          {creating ? "Creating..." : "+ New Game"}
        </button>
      </div>

      {error && <p style={styles.error}>{error}</p>}

      {games.length === 0 ? (
        <p style={styles.empty}>No games yet. Create one to begin.</p>
      ) : (
        <div style={styles.list}>
          {games.map((game) => (
            <button
              key={game.id}
              onClick={() => onSelectGame(game.id)}
              style={styles.gameCard}
            >
              <div style={styles.gameHeader}>
                <span style={styles.scenario}>{game.scenario}</span>
                <span
                  style={{
                    ...styles.status,
                    color: game.status === "active" ? "#40c040" : "#888",
                  }}
                >
                  {game.status}
                </span>
              </div>
              <div style={styles.gameMeta}>
                <span>Tick {game.current_tick}</span>
                <span style={styles.gameId}>
                  {game.id.slice(0, 8)}...
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: "800px",
    margin: "0 auto",
    padding: "32px 24px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "24px",
  },
  title: {
    fontSize: "24px",
    fontWeight: 600,
    color: "#e0e0e0",
  },
  createButton: {
    background: "#c8a860",
    color: "#0a0a0f",
    border: "none",
    borderRadius: "8px",
    padding: "10px 20px",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
  loading: {
    textAlign: "center" as const,
    padding: "64px",
    color: "#888",
  },
  error: {
    color: "#e04040",
    fontSize: "13px",
    marginBottom: "16px",
  },
  empty: {
    textAlign: "center" as const,
    color: "#666",
    padding: "48px",
    fontSize: "15px",
  },
  list: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "12px",
  },
  gameCard: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "16px 20px",
    cursor: "pointer",
    textAlign: "left" as const,
    color: "#e0e0e0",
    fontSize: "14px",
    width: "100%",
  },
  gameHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "8px",
  },
  scenario: {
    fontWeight: 600,
    fontSize: "16px",
  },
  status: {
    fontSize: "13px",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
  },
  gameMeta: {
    display: "flex",
    justifyContent: "space-between",
    color: "#888",
    fontSize: "13px",
  },
  gameId: {
    fontFamily: "monospace",
  },
};
