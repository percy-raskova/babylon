/**
 * Collapsible bottom panel — holds TimeSeries, EventLog, and GraphView tabs.
 */

import { ChevronDown, ChevronUp } from "lucide-react";
import { useUIStore } from "@/stores/uiStore";
import type { BottomTab } from "@/stores/uiStore";

const TABS: { id: BottomTab; label: string }[] = [
  { id: "timeseries", label: "Time Series" },
  { id: "events", label: "Events" },
  { id: "graph", label: "Graph" },
];

interface BottomPanelProps {
  children: React.ReactNode;
}

export function BottomPanel({ children }: BottomPanelProps) {
  const open = useUIStore((s) => s.bottomPanelOpen);
  const toggle = useUIStore((s) => s.toggleBottomPanel);
  const activeTab = useUIStore((s) => s.bottomTab);
  const setTab = useUIStore((s) => s.setBottomTab);

  return (
    <div
      className={`flex shrink-0 flex-col border-t border-soot bg-void transition-[height] duration-200 ${
        open ? "h-[260px]" : "h-9"
      }`}
    >
      {/* Tab bar */}
      <div className="flex shrink-0 items-center gap-1 px-3 py-1">
        <button
          onClick={toggle}
          className="mr-2 flex h-5 w-5 items-center justify-center rounded text-ash hover:text-silver"
          title={open ? "Collapse panel" : "Expand panel"}
        >
          {open ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </button>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setTab(tab.id);
              if (!open) toggle();
            }}
            className={`rounded px-3 py-1 text-xs font-medium ${
              activeTab === tab.id ? "bg-dark-metal text-gold" : "text-ash hover:text-silver"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {open && <div className="flex-1 overflow-hidden px-3 pb-3">{children}</div>}
    </div>
  );
}
