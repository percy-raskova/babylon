/**
 * BblPanel — bordered card with title/right/body slots.
 *
 * Paradox slot pattern: every panel exposes named slots (title, right, body).
 * Scenario authors can override one section without forking the whole panel.
 */

import type { ReactNode, CSSProperties } from "react";
import { BblLabel } from "./BblLabel";

interface BblPanelProps {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  accent?: string;
  className?: string;
  style?: CSSProperties;
  bodyClassName?: string;
}

export function BblPanel({
  title,
  right,
  children,
  accent,
  className = "",
  style,
  bodyClassName = "",
}: BblPanelProps) {
  const borderColor = accent ?? "#2a2a3a";
  return (
    <div
      className={`flex min-h-0 flex-col overflow-hidden rounded-lg bg-dark-metal ${className}`}
      style={{ border: `1px solid ${borderColor}`, ...style }}
    >
      {title && (
        <div className="flex shrink-0 items-center justify-between border-b border-soot bg-black/30 px-3 py-2">
          <BblLabel color="#c8a860">{title}</BblLabel>
          {right}
        </div>
      )}
      <div className={`min-h-0 flex-1 overflow-auto p-3 ${bodyClassName}`}>{children}</div>
    </div>
  );
}
