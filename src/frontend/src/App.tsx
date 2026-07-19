/**
 * Root application component — spec-110 B3 stage 2's cockpit routing,
 * extended by Track 2 T2-0 and Track 3 T3-5: /login, /lobby,
 * /game/:id/briefing, and the `/game/:id` LAYOUT (GameRoute) with its screen
 * children — the map (index, MapRoute), the Circuit (circuit, CircuitRoute),
 * and the Doctrine/"Line" page (doctrine, DoctrineRoute). Unauthenticated
 * requests are redirected to /login (checked via the session slice's real
 * `/accounts/whoami/` call).
 */

import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router";
import { useStore } from "@/store";
import { LoginRoute } from "@/routes/LoginRoute";
import { LobbyRoute } from "@/routes/LobbyRoute";
import { BriefingRoute } from "@/routes/BriefingRoute";
import { GameRoute } from "@/routes/GameRoute";
import { MapRoute } from "@/routes/MapRoute";
import { CircuitRoute } from "@/routes/CircuitRoute";
import { DoctrineRoute } from "@/routes/DoctrineRoute";
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
        path="/game/:id/briefing"
        element={isAuthed ? <BriefingRoute /> : <Navigate to="/login" replace />}
      />
      <Route path="/game/:id" element={isAuthed ? <GameRoute /> : <Navigate to="/login" replace />}>
        <Route index element={<MapRoute />} />
        <Route path="circuit" element={<CircuitRoute />} />
        <Route path="doctrine" element={<DoctrineRoute />} />
      </Route>
      <Route
        path="/observatory/*"
        element={isAuthed ? <ObservatoryRoute /> : <Navigate to="/login" replace />}
      />
      <Route path="*" element={<Navigate to={isAuthed ? "/lobby" : "/login"} replace />} />
    </Routes>
  );
}
