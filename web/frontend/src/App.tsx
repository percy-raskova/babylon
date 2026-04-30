/**
 * Root application component.
 *
 * Manages auth state and defines URL-based routes between Login, GameList, and GameShell.
 */

import { useCallback, useEffect, useState } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router";
import { get, post } from "@/api/client";
import { LoginPage } from "@/components/LoginPage";
import { GameList } from "@/components/GameList";
import { GameShell } from "@/components/layout/GameShell";
import { OrganizationsPage } from "@/components/OrganizationsPage";
import { ActionPage } from "@/components/ActionPage";
import { IntelPage } from "@/components/IntelPage";
import { DevHarness } from "@/DevHarness";
import type { AuthState } from "@/types/game";

// eslint-disable-next-line complexity -- router component has many route branches
export default function App() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [checking, setChecking] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await get<AuthState>("/accounts/whoami/");
        if (res.status === "ok" && res.data.is_authenticated) {
          setAuth(res.data);
        }
      } finally {
        setChecking(false);
      }
    }
    void checkAuth();
  }, []);

  const handleLogin = useCallback(
    (user: AuthState) => {
      setAuth(user);
      navigate("/games");
    },
    [navigate],
  );

  const handleLogout = useCallback(async () => {
    await post("/accounts/logout/");
    setAuth(null);
    navigate("/login");
  }, [navigate]);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center text-silver">Loading...</div>
    );
  }

  const isAuthed = auth?.is_authenticated === true;

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthed ? <Navigate to="/games" replace /> : <LoginPage onLogin={handleLogin} />}
      />

      <Route
        path="/games"
        element={
          isAuthed ? (
            <div className="flex min-h-screen flex-col">
              <nav className="flex shrink-0 items-center justify-between border-b border-soot bg-void px-6 py-3">
                <span className="text-base font-bold tracking-[4px] text-gold">BABYLON</span>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-silver">{auth?.username}</span>
                  <button
                    onClick={handleLogout}
                    className="rounded-md border border-wet-concrete px-3.5 py-1.5 text-[13px] text-silver hover:border-silver"
                  >
                    Logout
                  </button>
                </div>
              </nav>
              <GameList onSelectGame={(id) => navigate(`/games/${id}`)} />
            </div>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/games/:id/orgs"
        element={
          isAuthed ? (
            <OrganizationsPage username={auth?.username ?? ""} onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      <Route
        path="/games/:id/actions/:verb"
        element={
          isAuthed ? (
            <ActionPage username={auth?.username ?? ""} onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      <Route
        path="/games/:id/intel/:target_type/:target_id"
        element={
          isAuthed ? (
            <IntelPage username={auth?.username ?? ""} onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      <Route
        path="/games/:id"
        element={
          isAuthed ? (
            <GameShell
              username={auth?.username ?? ""}
              onBack={() => navigate("/games")}
              onLogout={handleLogout}
            />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      <Route path="/dev/hexmap" element={<DevHarness />} />

      <Route path="*" element={<Navigate to={isAuthed ? "/games" : "/login"} replace />} />
    </Routes>
  );
}
