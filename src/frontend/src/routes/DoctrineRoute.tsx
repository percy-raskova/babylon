/**
 * Doctrine route — Track 3 / T3-5: "The Line" screen, a sibling of the map
 * and the Circuit under the `/game/:id` layout (`GameRoute`), reached via
 * TopBar's "Doctrine" nav button. Copies the T2-0 routing pattern verbatim
 * (see `CircuitRoute`'s docstring): one `routes/*Route.tsx` file resolving
 * `:id` and handing off to a presentational screen component.
 */

import { useParams } from "react-router";
import { DoctrinePage } from "@/components/doctrine/DoctrinePage";

export function DoctrineRoute(): React.JSX.Element {
  const { id: gameId } = useParams<{ id: string }>();

  if (!gameId) {
    return <div className="flex h-screen items-center justify-center text-laser">No game id.</div>;
  }

  return <DoctrinePage gameId={gameId} />;
}
