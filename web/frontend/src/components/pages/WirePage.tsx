/**
 * WirePage - route wrapper for The Wire (spec 094).
 *
 * Mounted at /games/:id/wire under GameRouteShell.
 * Imports wire.css and renders WireApp with the game ID from params.
 */

import { useParams } from "react-router";
import { WireApp } from "@/components/wire/WireApp";
import "@/components/wire/wire.css";

export function WirePage() {
  const { id } = useParams<{ id: string }>();
  return <WireApp gameId={id ?? ""} />;
}
