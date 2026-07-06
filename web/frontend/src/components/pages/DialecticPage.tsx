/**
 * DialecticPage - route wrapper for the Dialectic screen (spec 095).
 *
 * Mounted at /games/:id/dialectic under GameRouteShell.
 * Renders DialecticSpread with the game ID from params.
 */

import { useParams } from "react-router";
import { DialecticSpread } from "@/components/dialectic/DialecticSpread";

export function DialecticPage() {
  const { id } = useParams<{ id: string }>();
  return <DialecticSpread gameId={id ?? ""} />;
}
