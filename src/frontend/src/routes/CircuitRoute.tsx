/**
 * Circuit route — Track 2 / T2-0+T2-1: the first routed sibling screen
 * under the `/game/:id` layout (`GameRoute`), reached via TopBar's
 * "Circuit" nav button. Thin `useParams` wrapper mirroring `MapRoute` — the
 * pattern a future screen (Track 3's Doctrine/"Line" page, T3-5) reuses
 * verbatim: one `routes/*Route.tsx` file resolving `:id` and handing off to
 * a presentational screen component.
 */

import { useParams } from "react-router";
import { CircuitPage } from "@/components/circuit/CircuitPage";

export function CircuitRoute(): React.JSX.Element {
  const { id: gameId } = useParams<{ id: string }>();

  if (!gameId) {
    return <div className="flex h-screen items-center justify-center text-laser">No game id.</div>;
  }

  return <CircuitPage gameId={gameId} />;
}
