/**
 * Root application component.
 *
 * Manages auth state and routes between Login, GameList, and GameView.
 */

import { useCallback, useEffect, useState } from "react";
import { get, post } from "@/api/client";
import { LoginPage } from "@/components/LoginPage";
import { GameList } from "@/components/GameList";
import { GameView } from "@/components/GameView";
import type { AuthState } from "@/types/game";

type View = { page: "login" } | { page: "games" } | { page: "game"; id: string };

export default function App() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [view, setView] = useState<View>({ page: "login" });
  const [checking, setChecking] = useState(true);

  // Check auth status on mount
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
    return <div style={styles.loading}>Loading...</div>;
  }

  return (
    <div style={styles.app}>
      {/* Top navigation bar when authenticated */}
      {auth?.is_authenticated && (
        <nav style={styles.nav}>
          <span style={styles.brand}>BABYLON</span>
          <div style={styles.navRight}>
            <span style={styles.username}>{auth.username}</span>
            <button onClick={handleLogout} style={styles.logoutButton}>
              Logout
            </button>
          </div>
        </nav>
      )}

      {/* Route to active view */}
      {view.page === "login" && <LoginPage onLogin={handleLogin} />}
      {view.page === "games" && <GameList onSelectGame={handleSelectGame} />}
      {view.page === "game" && (
        <GameView gameId={view.id} onBack={handleBackToGames} />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column" as const,
  },
  loading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    color: "#666",
    fontSize: "16px",
  },
  nav: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 24px",
    borderBottom: "1px solid #1a1a2a",
    background: "#0e0e18",
    flexShrink: 0,
  },
  brand: {
    color: "#c8a860",
    fontSize: "16px",
    fontWeight: 700,
    letterSpacing: "4px",
  },
  navRight: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
  },
  username: {
    color: "#888",
    fontSize: "14px",
  },
  logoutButton: {
    background: "none",
    border: "1px solid #2a2a3a",
    borderRadius: "6px",
    color: "#888",
    padding: "6px 14px",
    cursor: "pointer",
    fontSize: "13px",
  },
};
