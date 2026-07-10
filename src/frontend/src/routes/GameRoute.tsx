/**
 * Game route — resolves `:id` from the URL into `session.activeGameId`,
 * fires the one initial `/state/` fetch (the heartbeat's first tick only
 * lands after `HEARTBEAT_MS`), and mounts the persistent cockpit shell.
 */

import { useEffect } from "react";
import { useParams } from "react-router";
import { useStore } from "@/store";
import { useHeartbeat, useSpacebarShortcut } from "@/store/orchestrator";
import { AppShell } from "@/components/shell/AppShell";

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

  if (!gameId) {
    return <div className="flex h-screen items-center justify-center text-laser">No game id.</div>;
  }

  return <AppShell gameId={gameId} />;
}
