/**
 * Root application component — spec-110 B3 stage 2's 3-route cockpit:
 * /login, /lobby, /game/:id. Unauthenticated requests are redirected to
 * /login (checked via the session slice's real `/accounts/whoami/` call).
 */

import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router";
import { useStore } from "@/store";
import { LoginRoute } from "@/routes/LoginRoute";
import { LobbyRoute } from "@/routes/LobbyRoute";
import { GameRoute } from "@/routes/GameRoute";
import { ObservatoryRoute } from "@/observatory/ObservatoryRoute";

export default function App(): React.JSX.Element {
  const authChecking = useStore((s) => s.session.authChecking);
  const isAuthed = useStore((s) => s.session.auth?.is_authenticated === true);
  const checkAuth = useStore((s) => s.session.checkAuth);

  useEffect(() => {
    void checkAuth();
  }, [checkAuth]);

  if (authChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-void text-fog">Loading…</div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={isAuthed ? <Navigate to="/lobby" replace /> : <LoginRoute />} />
      <Route path="/lobby" element={isAuthed ? <LobbyRoute /> : <Navigate to="/login" replace />} />
      <Route
        path="/game/:id"
        element={isAuthed ? <GameRoute /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/observatory/*"
        element={isAuthed ? <ObservatoryRoute /> : <Navigate to="/login" replace />}
      />
      <Route path="*" element={<Navigate to={isAuthed ? "/lobby" : "/login"} replace />} />
    </Routes>
  );
}
