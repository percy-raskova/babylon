/**
 * IndexPage - story archive tab for The Wire.
 * Spec 094: ports IndexPage from wire-pages.jsx.
 */

import { useState } from "react";
import type { WireStoryIndex, WireSeverity } from "@/types/wire";

interface Props {
  index: WireStoryIndex[];
  activeId: string | null;
  onOpen: (storyId: string) => void;
}

type FilterOption = "all" | WireSeverity;

const FILTERS: FilterOption[] = ["all", "critical", "warning", "info"];

function sevColor(s: WireSeverity): string {
  if (s === "critical") return "var(--babylon-laser)";
  if (s === "warning") return "var(--babylon-heat)";
  return "var(--babylon-solidarity)";
}

export function IndexPage({ index, activeId, onOpen }: Props) {
  const [filter, setFilter] = useState<FilterOption>("all");
  const shown = filter === "all" ? index : index.filter((s) => s.severity === filter);

  return (
    <div className="h-full overflow-y-auto p-4" style={{ background: "var(--babylon-void)" }}>
      <div className="mb-4 flex items-baseline justify-between">
        <div>
          <div className="wire-label mb-1">{"\u25b8"} Wire Index</div>
          <div className="text-[18px] font-bold" style={{ color: "var(--babylon-bone)" }}>
            Recent dispatches
          </div>
          <div
            className="mt-1 text-[11px]"
            style={{
              color: "var(--babylon-fog)",
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.14em",
            }}
          >
            {index.length} STORIES
          </div>
        </div>
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`wire-btn-ghost ${filter === f ? "active" : ""}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-2">
        {shown.map((s) => {
          const isActive = s.id === activeId;
          return (
            <div
              key={s.id}
              onClick={() => onOpen(s.id)}
              className="cursor-pointer rounded border p-3 transition-colors"
              style={{
                background: "var(--babylon-concrete)",
                border: `1px solid ${isActive ? "var(--babylon-spire)" : "var(--babylon-rebar)"}`,
                borderLeft: `3px solid ${sevColor(s.severity)}`,
              }}
            >
              <div className="flex items-baseline gap-3">
                <span
                  className="text-[20px] font-bold"
                  style={{ color: "var(--babylon-spire)", fontFamily: "var(--font-mono)" }}
                >
                  {String(s.tick).padStart(4, "0")}
                </span>
                <span
                  className="text-[10px] font-semibold uppercase"
                  style={{ color: "var(--babylon-ash)", letterSpacing: "0.2em" }}
                >
                  {s.slug}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-3">
                <div className="border-l-2 pl-2" style={{ borderColor: "var(--babylon-cadre)" }}>
                  <div className="wire-label mb-1" style={{ color: "var(--babylon-cadre)" }}>
                    Continental
                  </div>
                  <div className="text-[12px]" style={{ color: "var(--babylon-bone)" }}>
                    {s.hed.c}
                  </div>
                </div>
                <div
                  className="border-l-2 pl-2"
                  style={{ borderColor: "var(--babylon-solidarity)" }}
                >
                  <div className="wire-label mb-1" style={{ color: "var(--babylon-solidarity)" }}>
                    Free Signal
                  </div>
                  <div
                    className="text-[11px]"
                    style={{ color: "#b4ffd1", fontFamily: "var(--font-mono)" }}
                  >
                    {s.hed.l}
                  </div>
                </div>
                <div className="border-l-2 pl-2" style={{ borderColor: "var(--babylon-rupture)" }}>
                  <div className="wire-label mb-1" style={{ color: "var(--babylon-rupture)" }}>
                    Cable
                  </div>
                  <div
                    className="text-[11px]"
                    style={{ color: "var(--babylon-bone)", fontFamily: "var(--font-mono)" }}
                  >
                    {s.hed.i}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
