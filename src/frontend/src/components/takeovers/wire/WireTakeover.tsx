/**
 * WireTakeover — thin overlay wrapper around the ported `WireApp` family
 * (spec-110 B5). Mirrors the old app's `WirePage` route wrapper (import
 * wire.css, render the family root with `gameId`) but as overlay content
 * instead of a route — `TakeoverOverlay` owns the escape/close chrome.
 */

import { WireApp } from "./WireApp";
import "./wire.css";

interface Props {
  gameId: string;
}

export function WireTakeover({ gameId }: Props): React.JSX.Element {
  return <WireApp gameId={gameId} />;
}
