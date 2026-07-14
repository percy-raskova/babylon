/**
 * BottomDrawer — "Trends"/"Economy" drawer hosting `TimeseriesChart` and
 * `EconomyDashboard` (architecture §1.2's `BottomStrip` disperse row;
 * `EconomyDashboard` added Wave 2 W2.2a). Both always render (never
 * JSX-conditional on `ui.chrome.bottomDrawer`) so they keep
 * `panels.timeseries`/`panels.economy` tick-fanned-out even while the
 * drawer is visually closed or on the other tab — the same
 * always-mounted-while-hidden rule the legacy `BottomStrip` enforced.
 * `FloatingPanel`'s own `collapsed` prop (not a conditional render) does
 * the outer hiding; the in-panel tab row below does the per-content hiding
 * via CSS only, same idiom.
 *
 * `ui.chrome.bottomDrawer`'s "events" arm deliberately doesn't duplicate
 * `EventsFeed` (that lives in `EventTray`, architecture §1.2) — it's a
 * diegetic pointer there instead, per DESIGN_BIBLE §7's "purge the admin
 * voice" ("No events loaded yet." is exactly the pattern that rule bans).
 *
 * Keeps `region-bottomstrip` (architecture §6 testid-contract risk).
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { TimeseriesChart } from "@/components/timeseries/TimeseriesChart";
import { EconomyDashboard } from "@/components/economy/EconomyDashboard";
import { keyButtonClass } from "./installerKit";

interface BottomDrawerProps {
  gameId: string;
}

export function BottomDrawer({ gameId }: BottomDrawerProps): React.JSX.Element {
  const bottomDrawer = useStore((s) => s.ui.chrome.bottomDrawer);
  const setBottomDrawer = useStore((s) => s.ui.setBottomDrawer);

  return (
    <FloatingPanel
      anchor="bottom"
      title={bottomDrawer === "economy" ? "Economy" : "Trends"}
      collapsed={bottomDrawer === "none"}
      onToggle={() => setBottomDrawer(bottomDrawer === "none" ? "trends" : "none")}
      testId="region-bottomstrip"
    >
      {/* Tab row — the "toggle following the existing pattern" for
          reaching the economy content: two keyed buttons swap which
          always-mounted child is visible, same gold-inverse-video
          selection grammar as every other chrome tab cluster
          (installerKit's keyButtonClass). */}
      <div className="mb-1 flex gap-1 px-1" role="tablist" aria-label="Bottom drawer content">
        <button
          type="button"
          role="tab"
          aria-selected={bottomDrawer === "trends"}
          data-testid="bottomdrawer-tab-trends"
          onClick={() => setBottomDrawer("trends")}
          className={keyButtonClass(bottomDrawer === "trends", "px-2 py-0.5 text-[10px]")}
        >
          Trends
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={bottomDrawer === "economy"}
          data-testid="bottomdrawer-tab-economy"
          onClick={() => setBottomDrawer("economy")}
          className={keyButtonClass(bottomDrawer === "economy", "px-2 py-0.5 text-[10px]")}
        >
          Economy
        </button>
      </div>

      {/* h-48 (not h-full): the anchor="bottom" panel is shrink-to-fit (no
          `top`), so an h-full child + recharts ResponsiveContainer height="100%"
          resolves to 0 and the chart vanishes. A definite pixel height gives the
          ResponsiveContainer something to measure (spec-113 Phase V). */}
      <div className={bottomDrawer === "trends" ? "h-48" : "hidden"}>
        <TimeseriesChart gameId={gameId} />
      </div>
      <div className={bottomDrawer === "economy" ? "h-48 overflow-y-auto" : "hidden"}>
        <EconomyDashboard gameId={gameId} />
      </div>
      {bottomDrawer === "events" && (
        <p className="p-3 text-[11px] italic text-ksbc-muted-2">
          The dispatch already runs in the tray, top right.
        </p>
      )}
    </FloatingPanel>
  );
}
