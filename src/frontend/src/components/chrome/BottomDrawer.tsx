/**
 * BottomDrawer — chrome stub, "Trends" drawer hosting `TimeseriesChart`
 * (architecture §1.2's `BottomStrip` disperse row). `TimeseriesChart`
 * always renders (never JSX-conditional on `ui.chrome.bottomDrawer`) so it
 * keeps `panels.timeseries` tick-fanned-out even while the drawer is
 * visually closed — the same always-mounted-while-hidden rule the legacy
 * `BottomStrip` enforced. `FloatingPanel`'s own `collapsed` prop (not a
 * conditional render) does the hiding.
 *
 * `ui.chrome.bottomDrawer`'s "events" arm is a placeholder here —
 * `EventsFeed` lives in `EventTray` (architecture §1.2), not duplicated
 * into this drawer too. Lane E decides what "events" mode shows.
 *
 * Keeps `region-bottomstrip` (architecture §6 testid-contract risk).
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { TimeseriesChart } from "@/components/timeseries/TimeseriesChart";

interface BottomDrawerProps {
  gameId: string;
}

export function BottomDrawer({ gameId }: BottomDrawerProps): React.JSX.Element {
  const bottomDrawer = useStore((s) => s.ui.chrome.bottomDrawer);
  const setBottomDrawer = useStore((s) => s.ui.setBottomDrawer);

  return (
    <FloatingPanel
      anchor="bottom"
      title="Trends"
      collapsed={bottomDrawer === "none"}
      onToggle={() => setBottomDrawer(bottomDrawer === "none" ? "trends" : "none")}
      testId="region-bottomstrip"
    >
      <div className={bottomDrawer === "events" ? "hidden" : "h-full"}>
        <TimeseriesChart gameId={gameId} />
      </div>
      {bottomDrawer === "events" && (
        <p className="p-3 text-[11px] italic text-shroud">Events — see the event tray.</p>
      )}
    </FloatingPanel>
  );
}
