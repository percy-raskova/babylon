/**
 * SpeedControls — chrome stub (architecture §1.2's `TimeControls` →
 * `SpeedControls` rewrite row; Lane A hands this file to Lane E after
 * merge). v1 hosts the legacy `TimeControls` content verbatim (Pause/
 * Step/Play + `time-status`) so the TopBar migration is behavior-
 * preserving; Lane E owns adding the 1x/2x/5x speed cluster
 * (architecture §4.1, `timeSlice.speed`).
 */

import { TimeControls } from "@/components/shell/TimeControls";

interface SpeedControlsProps {
  gameId: string;
}

export function SpeedControls({ gameId }: SpeedControlsProps): React.JSX.Element {
  return <TimeControls gameId={gameId} />;
}
