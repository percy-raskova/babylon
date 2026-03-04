/**
 * Collapsible bottom panel — holds TimeSeries, EventLog, GraphView, and Notifications tabs.
 * Height read from uiStore for resize persistence. Drag-to-resize via top-edge handle.
 */

import { useCallback, useRef } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useUIStore } from "@/stores/uiStore";
import type { BottomTab } from "@/stores/uiStore";

const TABS: { id: BottomTab; label: string }[] = [
  { id: "timeseries", label: "Time Series" },
  { id: "events", label: "Events" },
  { id: "graph", label: "Graph" },
  { id: "notifications", label: "Notifications" },
];

interface BottomPanelProps {
  children: React.ReactNode;
}

export function BottomPanel({ children }: BottomPanelProps) {
  const open = useUIStore((s) => s.bottomPanelOpen);
  const toggle = useUIStore((s) => s.toggleBottomPanel);
  const activeTab = useUIStore((s) => s.bottomTab);
  const setTab = useUIStore((s) => s.setBottomTab);
  const height = useUIStore((s) => s.bottomPanelHeight);
  const setHeight = useUIStore((s) => s.setBottomPanelHeight);
  const unreadCount = useUIStore((s) => s.unreadCount);
  const dragging = useRef(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      const startY = e.clientY;
      const startHeight = height;

      const onMove = (moveEvt: MouseEvent) => {
        if (!dragging.current) return;
        // Dragging up = increasing height
        const delta = startY - moveEvt.clientY;
        setHeight(startHeight + delta);
      };

      const onUp = () => {
        dragging.current = false;
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [height, setHeight],
  );

  return (
    <div
      className="relative flex shrink-0 flex-col border-t border-soot bg-void transition-[height] duration-200"
      style={{ height: open ? height : 36 }}
    >
      {/* Resize handle */}
      {open && (
        <div
          onMouseDown={handleMouseDown}
          className="absolute -top-1 left-0 z-20 h-2 w-full cursor-row-resize hover:bg-gold/10"
        />
      )}
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
            className={`relative rounded px-3 py-1 text-xs font-medium ${
              activeTab === tab.id ? "bg-dark-metal text-gold" : "text-ash hover:text-silver"
            }`}
          >
            {tab.label}
            {tab.id === "notifications" && unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-crimson px-1 text-[8px] font-bold text-bone">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {open && <div className="flex-1 overflow-hidden px-3 pb-3">{children}</div>}
    </div>
  );
}
