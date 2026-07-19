/**
 * Game route — the `/game/:id` LAYOUT route (Track 2 T2-0: the shared
 * routing pattern every screen adopts). Resolves `:id` from the URL into
 * `session.activeGameId`, fires the one initial `/state/` fetch (the
 * heartbeat's first tick only lands after `HEARTBEAT_MS`), starts the
 * heartbeat/keyboard-shortcut machinery, and renders whichever screen
 * matched underneath it via `<Outlet/>` — the map (index route,
 * `MapRoute`/`AppShell`), the Circuit (`circuit`, `CircuitRoute`), and
 * later Track 3's Doctrine/"Line" page.
 *
 * This is deliberately a LAYOUT, not a leaf: the session/heartbeat effects
 * below must survive a player switching screens (Map ↔ Circuit ↔ ...) —
 * two independent top-level routes each owning their own
 * setActiveGame/useHeartbeat would tear the session down and restart it on
 * every screen switch (the heartbeat is a `useEffect` tied to whichever
 * component mounts it). Owning it once, here, at the `/game/:id` layout
 * level, means the clock never stops just because the URL grew a suffix.
 */

import { useEffect } from "react";
import { Outlet, useParams } from "react-router";
import { useStore } from "@/store";
import { useHeartbeat, useSpacebarShortcut, useLensCycleShortcut } from "@/store/orchestrator";

export function GameRoute(): React.JSX.Element {
  const { id: gameId } = useParams<{ id: string }>();
  const setActiveGame = useStore((s) => s.session.setActiveGame);
  const fetchState = useStore((s) => s.world.fetchState);

  useEffect(() => {
    if (!gameId) return;
    setActiveGame(gameId);
    void fetchState(gameId);
    return () => setActiveGame(null);
  }, [gameId, setActiveGame, fetchState]);

  useHeartbeat(gameId ?? null);
  useSpacebarShortcut(gameId ?? null);
  useLensCycleShortcut(gameId ?? null);

  if (!gameId) {
    return <div className="flex h-screen items-center justify-center text-laser">No game id.</div>;
  }

  return <Outlet />;
}
