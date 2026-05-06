/**
 * BblData — monospace data readout.
 *
 * Used for numeric values, tick counters, percentages.
 * Always rendered in the mono font stack.
 */

import type { ReactNode, CSSProperties } from "react";

interface BblDataProps {
  children: ReactNode;
  color?: string;
  size?: number;
  className?: string;
  style?: CSSProperties;
}

export function BblData({
  children,
  color = "#c8a860",
  size = 12,
  className = "",
  style,
}: BblDataProps) {
  return (
    <span
      className={`font-semibold ${className}`}
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: size,
        color,
        ...style,
      }}
    >
      {children}
    </span>
  );
}
