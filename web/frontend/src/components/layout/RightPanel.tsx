/**
 * Collapsible right sidebar — holds ActionPanel and OrgDashboard.
 */

import { ChevronRight, ChevronLeft } from "lucide-react";
import { useUIStore } from "@/stores/uiStore";

interface RightPanelProps {
  children: React.ReactNode;
}

export function RightPanel({ children }: RightPanelProps) {
  const open = useUIStore((s) => s.rightPanelOpen);
  const toggle = useUIStore((s) => s.toggleRightPanel);

  return (
    <div
      className={`relative flex shrink-0 flex-col border-l border-soot bg-void transition-[width] duration-200 ${
        open ? "w-[360px]" : "w-10"
      }`}
    >
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
