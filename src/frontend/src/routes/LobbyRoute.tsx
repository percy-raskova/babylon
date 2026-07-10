/**
 * Lobby route — real `/api/games/` + `/api/scenarios/` list, minimal
 * create-game form. Mirrors the legacy `GameList`'s data flow through the
 * session slice instead of a local `useEffect` fetch.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useStore } from "@/store";

export function LobbyRoute(): React.JSX.Element {
  const auth = useStore((s) => s.session.auth);
  const games = useStore((s) => s.session.games);
  const gamesLoading = useStore((s) => s.session.gamesLoading);
  const scenarios = useStore((s) => s.session.scenarios);
  const error = useStore((s) => s.session.error);
  const fetchGames = useStore((s) => s.session.fetchGames);
  const fetchScenarios = useStore((s) => s.session.fetchScenarios);
  const createGame = useStore((s) => s.session.createGame);
  const logout = useStore((s) => s.session.logout);
  const navigate = useNavigate();

  // "" means "no explicit user pick yet" — the effective selection falls
  // back to the first fetched scenario (computed below during render, not
  // synced via an effect: there is nothing to derive once fetched data
  // arrives that render can't compute directly).
  const [selectedScenario, setSelectedScenario] = useState("");
  const [creating, setCreating] = useState(false);
  const effectiveScenario = selectedScenario || (scenarios[0]?.key ?? "");

  useEffect(() => {
    fetchGames();
    fetchScenarios();
  }, [fetchGames, fetchScenarios]);

  async function handleCreate(): Promise<void> {
    if (!effectiveScenario) return;
    setCreating(true);
    const id = await createGame({ scenario: effectiveScenario });
    setCreating(false);
    if (id) navigate(`/game/${id}`);
  }

  async function handleLogout(): Promise<void> {
    await logout();
    navigate("/login");
  }

  return (
    <div className="flex min-h-screen flex-col bg-void">
      <header className="flex items-center justify-between border-b border-rebar px-6 py-3">
        <span className="text-sm font-bold tracking-[4px] text-spire">BABYLON</span>
        <div className="flex items-center gap-4">
          <span className="text-sm text-fog">{auth?.username}</span>
          <button
            onClick={() => void handleLogout()}
            className="rounded-md border border-wet-steel px-3 py-1.5 text-[12px] text-fog hover:border-fog"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 px-6 py-8">
        <section className="rounded-lg border border-rebar bg-concrete p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="m-0 text-sm font-semibold uppercase tracking-wider text-spire">
              New Operation
            </h2>
            {scenarios.length > 0 && (
              <select
                value={effectiveScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="rounded border border-wet-steel bg-void px-2 py-1 text-[11px] text-bone"
              >
                {scenarios.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
          </div>
          <button
            onClick={() => void handleCreate()}
            disabled={creating || !effectiveScenario}
            className="rounded-md bg-spire px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] text-void hover:brightness-110 disabled:opacity-50"
          >
            {creating ? "Creating…" : "+ New Game"}
          </button>
        </section>

        {error && (
          <p role="alert" className="text-[12px] text-laser">
            {error}
          </p>
        )}

        <section className="rounded-lg border border-rebar bg-concrete p-4">
          <h2 className="m-0 mb-3 text-sm font-semibold uppercase tracking-wider text-spire">
            Your Games ({games.length})
          </h2>
          {gamesLoading && <p className="text-[12px] text-ash">Loading games…</p>}
          {!gamesLoading && games.length === 0 && (
            <p className="py-6 text-center text-[13px] text-ash">
              No operations yet — create one to begin organizing.
            </p>
          )}
          {!gamesLoading && games.length > 0 && (
            <div className="flex flex-col gap-2">
              {games.map((game) => (
                <button
                  key={game.id}
                  onClick={() => navigate(`/game/${game.id}`)}
                  className="flex w-full items-center justify-between rounded-md border border-rebar bg-void px-4 py-3 text-left hover:border-spire"
                >
                  <span className="text-[13px] font-semibold text-bone">{game.scenario}</span>
                  <span className="font-mono text-[11px] text-fog">Tick {game.current_tick}</span>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
