/**
 * ChronicleTakeover — thin overlay wrapper around the ported
 * `EndStateScreen` family (spec-110 B5). `EndStateScreen` imports its own
 * `chronicle.css`; `TakeoverOverlay` owns the escape/close chrome.
 */

import { EndStateScreen } from "./EndStateScreen";

interface Props {
  gameId: string;
}

export function ChronicleTakeover({ gameId }: Props): React.JSX.Element {
  return <EndStateScreen gameId={gameId} />;
}
