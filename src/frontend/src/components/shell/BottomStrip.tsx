/**
 * Bottom Strip — collapsible events feed + timeseries panel. Both are
 * always mounted while the shell is up (collapse only changes the grid
 * row's height via `AppShell`), so `panels.timeseries` stays fanned out
 * on every tick regardless of visual state.
 */

import { useStore } from "@/store";
import { EventsFeed } from "@/components/events/EventsFeed";
import { TimeseriesChart } from "@/components/timeseries/TimeseriesChart";

interface BottomStripProps {
  gameId: string;
}

export function BottomStrip({ gameId }: BottomStripProps): React.JSX.Element {
  const collapsed = useStore((s) => s.ui.bottomStripCollapsed);
  const toggle = useStore((s) => s.ui.toggleBottomStrip);
  const activeTab = useStore((s) => s.ui.activeDockTab);
  const setActiveTab = useStore((s) => s.ui.setActiveDockTab);

  return (
    <footer
      data-testid="region-bottomstrip"
      aria-label="BottomStrip"
      className="col-span-3 row-start-3 flex flex-col overflow-hidden border-t border-rebar"
    >
      <div className="flex shrink-0 items-center gap-1 border-b border-rebar bg-concrete px-2 py-1">
        <button
          onClick={toggle}
          aria-expanded={!collapsed}
          className="rounded border border-rebar px-1.5 py-0.5 text-[10px] text-fog"
        >
          {collapsed ? "▲" : "▼"}
        </button>
        <TabButton active={activeTab === "events"} onClick={() => setActiveTab("events")}>
          Events
        </TabButton>
        <TabButton active={activeTab === "timeseries"} onClick={() => setActiveTab("timeseries")}>
          Time Series
        </TabButton>
      </div>
      {/* Both tabs stay mounted regardless of which is active or whether the
          strip is collapsed — `TimeseriesChart` owns `panels.timeseries`'s
          mount/fetch lifecycle and must keep it fanned out on every tick
          even while hidden; visibility is CSS-only, never a JSX unmount. */}
      <div className={`min-h-0 flex-1 overflow-y-auto ${collapsed ? "hidden" : ""}`}>
        <div className={activeTab === "events" ? "" : "hidden"}>
          <EventsFeed />
        </div>
        <div className={`h-full ${activeTab === "timeseries" ? "" : "hidden"}`}>
          <TimeseriesChart gameId={gameId} />
        </div>
      </div>
    </footer>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`rounded px-2 py-1 text-[10px] font-semibold uppercase tracking-widest ${
        active ? "bg-spire/10 text-spire" : "text-ash hover:text-fog"
      }`}
    >
      {children}
    </button>
  );
}
