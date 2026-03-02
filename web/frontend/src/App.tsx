/**
 * Root application component.
 *
 * Manages auth state and routes between Login, GameList, and GameShell.
 */

import { useCallback, useEffect, useState } from "react";
import { get, post } from "@/api/client";
import { LoginPage } from "@/components/LoginPage";
import { GameList } from "@/components/GameList";
import { GameShell } from "@/components/layout/GameShell";
import type { AuthState } from "@/types/game";

type View = { page: "login" } | { page: "games" } | { page: "game"; id: string };

export default function App() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [view, setView] = useState<View>({ page: "login" });
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    async function checkAuth() {
      const res = await get<AuthState>("/accounts/whoami/");
      if (res.status === "ok" && res.data.is_authenticated) {
        setAuth(res.data);
        setView({ page: "games" });
      }
      setChecking(false);
    }
    void checkAuth();
  }, []);

  const handleLogin = useCallback((user: AuthState) => {
    setAuth(user);
    setView({ page: "games" });
  }, []);

  const handleLogout = useCallback(async () => {
    await post("/accounts/logout/");
    setAuth(null);
    setView({ page: "login" });
  }, []);

  const handleSelectGame = useCallback((gameId: string) => {
    setView({ page: "game", id: gameId });
  }, []);

  const handleBackToGames = useCallback(() => {
    setView({ page: "games" });
  }, []);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center text-silver">Loading...</div>
    );
  }

  // GameShell is a full-viewport layout with its own TopBar (includes nav + logout)
  if (view.page === "game" && auth?.is_authenticated) {
    return (
      <GameShell
        gameId={view.id}
        username={auth.username ?? ""}
        onBack={handleBackToGames}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      {auth?.is_authenticated && view.page === "games" && (
        <nav className="flex shrink-0 items-center justify-between border-b border-soot bg-void px-6 py-3">
          <span className="text-base font-bold tracking-[4px] text-gold">BABYLON</span>
          <div className="flex items-center gap-4">
            <span className="text-sm text-silver">{auth.username}</span>
            <button
              onClick={handleLogout}
              className="rounded-md border border-wet-concrete px-3.5 py-1.5 text-[13px] text-silver hover:border-silver"
            >
              Logout
            </button>
          </div>
        </nav>
      )}

      {view.page === "login" && <LoginPage onLogin={handleLogin} />}
      {view.page === "games" && <GameList onSelectGame={handleSelectGame} />}
    </div>
  );
}
