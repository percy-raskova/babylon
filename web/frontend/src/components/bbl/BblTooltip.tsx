/**
 * BblTooltip — Paradox-style tooltip with optional breakdown.
 *
 * Mirrors `GetScriptValueBreakdown` — every aggregate stat (Heat, Cohesion,
 * Consciousness) can show a "Base + contributors" provenance on hover.
 * Per the spec, every numeric value the player sees should have a breakdown route.
 */

import { useState, useRef, useCallback, type ReactNode } from "react";

export interface BreakdownEntry {
  label: string;
  value: number;
}

interface BblTooltipProps {
  children: ReactNode;
  text?: string;
  breakdown?: BreakdownEntry[];
  total?: number;
}

export function BblTooltip({ children, text, breakdown, total }: BblTooltipProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const ref = useRef<HTMLSpanElement>(null);

  const handleEnter = useCallback(() => {
    if (ref.current) {
      const r = ref.current.getBoundingClientRect();
      setPos({ x: r.left + r.width / 2, y: r.top - 6 });
    }
    setOpen(true);
  }, []);

  const hasContent = text || (breakdown && breakdown.length > 0);
  if (!hasContent) return <>{children}</>;

  return (
    <span
      ref={ref}
      className="relative inline-block cursor-help"
      onMouseEnter={handleEnter}
      onMouseLeave={() => setOpen(false)}
    >
      {children}
      {open && (
        <div
          className="pointer-events-none fixed z-[9999] min-w-[200px] max-w-[280px] rounded-md border border-gold bg-void p-2"
          style={{
            left: pos.x,
            top: pos.y,
            transform: "translate(-50%, -100%)",
            boxShadow: "0 0 24px rgba(0,0,0,.9), 0 0 8px rgba(200,168,96,.2)",
            fontFamily: "var(--font-sans)",
          }}
        >
          {text && <div className="text-[11px] leading-snug text-bone">{text}</div>}
          {breakdown && breakdown.length > 0 && (
            <div>
              <div className="mb-1 border-b border-soot pb-1 text-[9px] uppercase tracking-[0.2em] text-ash">
                Breakdown
              </div>
              {breakdown.map((b, i) => (
                <div key={i} className="mb-0.5 flex justify-between text-[10px]">
                  <span className="text-silver">{b.label}</span>
                  <span
                    className="font-mono"
                    style={{ color: b.value < 0 ? "#e06060" : "#c8a860" }}
                  >
                    {b.value > 0 ? "+" : ""}
                    {b.value.toFixed(3)}
                  </span>
                </div>
              ))}
              {total !== undefined && (
                <div className="mt-1 flex justify-between border-t border-soot pt-1 text-[11px] font-semibold text-gold">
                  <span>Total</span>
                  <span className="font-mono">{total.toFixed(3)}</span>
                </div>
              )}
            </div>
          )}
          {/* Tip arrow */}
          <div
            className="absolute left-1/2 -translate-x-1/2"
            style={{
              bottom: -6,
              width: 0,
              height: 0,
              borderLeft: "5px solid transparent",
              borderRight: "5px solid transparent",
              borderTop: "6px solid #c8a860",
            }}
          />
        </div>
      )}
    </span>
  );
}
