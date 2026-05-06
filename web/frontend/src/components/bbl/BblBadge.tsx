/**
 * BblBadge — pill badge for tags, status, and categories.
 *
 * Used for class character labels, OODA phase, edge types,
 * composition tags, and filter chips.
 */

import type { ReactNode, CSSProperties } from "react";

interface BblBadgeProps {
  children: ReactNode;
  color?: string;
  bg?: string;
  className?: string;
  style?: CSSProperties;
}

export function BblBadge({
  children,
  color = "#888",
  bg = "rgba(255,255,255,.04)",
  className = "",
  style,
}: BblBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.15em] ${className}`}
      style={{
        color,
        background: bg,
        border: `1px solid ${color}33`,
        fontFamily: "var(--font-sans)",
        ...style,
      }}
    >
      {children}
    </span>
  );
}
