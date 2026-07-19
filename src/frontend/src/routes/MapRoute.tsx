/**
 * Map route — the index child of the `/game/:id` layout (`GameRoute`): the
 * default screen, "home" per spec-117 §5 ("the map is home; each front gets
 * a room of its own"). Thin `useParams` wrapper mirroring `CircuitRoute`'s
 * pattern (Track 2 T2-0) — `GameRoute` (the parent layout) already
 * validated `:id` is present before rendering the `<Outlet/>` this mounts
 * into, so the guard here is belt-only, same idiom as every other
 * `routes/*.tsx` file.
 */

import { useParams } from "react-router";
import { AppShell } from "@/components/shell/AppShell";

export function MapRoute(): React.JSX.Element {
  const { id: gameId } = useParams<{ id: string }>();

  if (!gameId) {
    return <div className="flex h-screen items-center justify-center text-laser">No game id.</div>;
  }

  return <AppShell gameId={gameId} />;
}
