/**
 * WireWindow — app chrome for The Wire (title bar + tab bar).
 * Spec 094: ports wire-window.jsx as fresh TypeScript.
 */

import type { ReactNode } from "react";

export interface WireTab {
  id: string;
  label: string;
  count?: number;
  dot?: string;
}

interface WireWindowProps {
  tabs: WireTab[];
  activeId: string;
  onTab: (id: string) => void;
  badge: ReactNode;
  children: ReactNode;
}

export function WireWindow({ tabs, activeId, onTab, badge, children }: WireWindowProps) {
  return (
    <div
      className="flex h-full flex-col overflow-hidden"
      style={{ background: "var(--babylon-void)" }}
    >
      {/* Title bar */}
      <div
        className="flex shrink-0 items-center gap-3 border-b px-3 py-2"
        style={{
          borderColor: "var(--babylon-rebar)",
          background: "linear-gradient(180deg, #0b0e15 0%, #07090d 100%)",
        }}
      >
        <div className="flex gap-1.5">
          <span
            title="close"
            className="h-2.5 w-2.5 rounded-full"
            style={{ background: "var(--babylon-laser)", boxShadow: "0 0 4px rgba(255,51,68,0.5)" }}
          />
          <span
            title="minimize"
            className="h-2.5 w-2.5 rounded-full"
            style={{ background: "var(--babylon-heat)", boxShadow: "0 0 4px rgba(217,122,44,0.4)" }}
          />
          <span
            title="maximize"
            className="h-2.5 w-2.5 rounded-full"
            style={{
              background: "var(--babylon-solidarity)",
              boxShadow: "0 0 4px rgba(95,191,122,0.45)",
            }}
          />
        </div>

        <div
          className="flex items-baseline gap-2"
          style={{ marginLeft: "auto", marginRight: "auto" }}
        >
          <span
            className="text-[12px] font-bold"
            style={{ letterSpacing: "0.42em", color: "var(--babylon-spire)" }}
          >
            THE WIRE
          </span>
        </div>

        <div className="flex items-center gap-2" style={{ marginLeft: "auto" }}>
          {badge}
        </div>
      </div>

      {/* Tab bar */}
      <div
        className="flex shrink-0 items-stretch border-b pl-2"
        style={{ borderColor: "var(--babylon-rebar)", background: "#0a0d13" }}
      >
        {tabs.map((t) => {
          const active = t.id === activeId;
          return (
            <button
              key={t.id}
              onClick={() => onTab(t.id)}
              className="flex items-center gap-2 border-r px-4 py-2 text-[9px] font-medium uppercase transition-colors"
              style={{
                fontFamily: "var(--font-mono)",
                letterSpacing: "0.2em",
                background: active ? "var(--babylon-void)" : "transparent",
                color: active ? "var(--babylon-spire)" : "var(--babylon-fog)",
                fontWeight: active ? 700 : 500,
                borderTop: active ? "2px solid var(--babylon-spire)" : "2px solid transparent",
                borderColor: "var(--babylon-rebar)",
                cursor: "pointer",
              }}
            >
              {t.label}
              {t.count != null && (
                <span
                  className="rounded-full px-1.5 py-0.5 text-[8px]"
                  style={{
                    fontFamily: "var(--font-mono)",
                    background: active ? "rgba(77,217,230,0.12)" : "var(--babylon-rebar)",
                    color: active ? "var(--babylon-spire)" : "var(--babylon-ash)",
                  }}
                >
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="relative min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
