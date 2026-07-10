/**
 * DialecticTakeover — thin overlay wrapper around the ported
 * `DialecticSpread` family (spec-110 B5). `DialecticSpread` imports its own
 * `dialectic.css`; `TakeoverOverlay` owns the escape/close chrome.
 */

import { DialecticSpread } from "./DialecticSpread";

interface Props {
  gameId: string;
}

export function DialecticTakeover({ gameId }: Props): React.JSX.Element {
  return <DialecticSpread gameId={gameId} />;
}
