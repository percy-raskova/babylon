/**
 * Collapsible right sidebar — holds ActionPanel and OrgDashboard.
 * Supports drag-to-resize via left-edge handle (280-600px range).
 */

import { useCallback, useRef } from "react";
import { ChevronRight, ChevronLeft } from "lucide-react";
import { useUIStore } from "@/stores/uiStore";

interface RightPanelProps {
  children: React.ReactNode;
}

export function RightPanel({ children }: RightPanelProps) {
  const open = useUIStore((s) => s.rightPanelOpen);
  const toggle = useUIStore((s) => s.toggleRightPanel);
  const width = useUIStore((s) => s.rightPanelWidth);
  const setWidth = useUIStore((s) => s.setRightPanelWidth);
  const dragging = useRef(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      const startX = e.clientX;
      const startWidth = width;

      const onMove = (moveEvt: MouseEvent) => {
        if (!dragging.current) return;
        // Dragging left = increasing width (panel is on right side)
        const delta = startX - moveEvt.clientX;
        setWidth(startWidth + delta);
      };

      const onUp = () => {
        dragging.current = false;
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [width, setWidth],
  );

  return (
    <div
      className="relative flex shrink-0 flex-col border-l border-soot bg-void transition-[width] duration-200"
      style={{ width: open ? width : 40 }}
    >
      {/* Resize handle */}
      {open && (
        <div
          onMouseDown={handleMouseDown}
          className="absolute -left-1 top-0 z-20 h-full w-2 cursor-col-resize hover:bg-gold/10"
        />
      )}

      <button
        onClick={toggle}
        className="absolute -left-3 top-3 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-wet-concrete bg-dark-metal text-ash hover:text-silver"
        title={open ? "Collapse sidebar" : "Expand sidebar"}
      >
        {open ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
      {open && <div className="flex flex-1 flex-col gap-3 overflow-hidden p-3">{children}</div>}
    </div>
  );
}
