/**
 * ChroniclePage - route wrapper for the chronicle end-screen (spec 095).
 *
 * Mounted at /games/:id/chronicle under GameRouteShell.
 * Renders EndStateScreen with the game ID from params.
 */

import { useParams } from "react-router";
import { EndStateScreen } from "@/components/chronicle/EndStateScreen";

export function ChroniclePage() {
  const { id } = useParams<{ id: string }>();
  return <EndStateScreen gameId={id ?? ""} />;
}
