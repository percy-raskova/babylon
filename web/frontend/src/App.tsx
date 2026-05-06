/**
 * Root application component — v2 16-route architecture.
 *
 * Pre-game routes (login, games) render without game chrome.
 * In-game routes nest under GameRouteShell for persistent TopBar + NavRail.
 */

import { useCallback, useEffect, useState } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router";
import { get, post } from "@/api/client";
import { LoginPage } from "@/components/LoginPage";
import { GameList } from "@/components/GameList";
import { GameRouteShell } from "@/components/layout/GameRouteShell";
import { BriefingPage } from "@/components/pages/BriefingPage";
import { OrgsPage } from "@/components/pages/OrgsPage";
import { VerbPage } from "@/components/pages/VerbPage";
import { ResultsPage } from "@/components/pages/ResultsPage";
import { IntelPageV2 } from "@/components/pages/IntelPageV2";
import { AnalysisPage } from "@/components/pages/AnalysisPage";
import { DevHarness } from "@/DevHarness";
import type { AuthState } from "@/types/game";

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
      {/* Pre-game routes — no game chrome */}
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

      {/* In-game routes — nested under GameRouteShell */}
      <Route
        path="/games/:id"
        element={
          isAuthed ? (
            <GameRouteShell username={auth?.username ?? ""} onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      >
        {/* Core game-loop routes */}
        <Route index element={<BriefingPage />} />
        <Route path="orgs" element={<OrgsPage />} />
        <Route path="results" element={<ResultsPage />} />

        {/* Intel routes — powered by IntelPageV2 */}
        <Route path="intel" element={<IntelPageV2 />} />
        <Route path="intel/:targetType/:targetId" element={<IntelPageV2 />} />

        {/* 9 verb routes — all handled by VerbPage */}
        <Route path="actions/:verb" element={<VerbPage />} />

        {/* Analysis page */}
        <Route path="analysis" element={<AnalysisPage />} />

        {/* Event log */}
        <Route
          path="log"
          element={
            <div className="flex h-full items-center justify-center text-sm text-ash">
              Event log — coming soon
            </div>
          }
        />
      </Route>

      <Route path="/dev/hexmap" element={<DevHarness />} />
      <Route path="*" element={<Navigate to={isAuthed ? "/games" : "/login"} replace />} />
    </Routes>
  );
}
