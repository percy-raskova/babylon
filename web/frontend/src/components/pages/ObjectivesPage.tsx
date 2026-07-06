/**
 * ObjectivesPage - route wrapper for the objectives tracker (spec 095).
 *
 * Mounted at /games/:id/objectives under GameRouteShell.
 * Renders ObjectivesTracker with the game ID from params.
 */

import { useParams } from "react-router";
import { ObjectivesTracker } from "@/components/objectives/ObjectivesTracker";

export function ObjectivesPage() {
  const { id } = useParams<{ id: string }>();
  return <ObjectivesTracker gameId={id ?? ""} />;
}
