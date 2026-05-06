/**
 * BblLabel — uppercase micro-label.
 *
 * Constitution VII visual vocabulary: category labels, section headers,
 * axis labels. Always uppercased with wide tracking.
 */

import type { ReactNode, CSSProperties } from "react";

interface BblLabelProps {
  children: ReactNode;
  color?: string;
  className?: string;
  style?: CSSProperties;
}

export function BblLabel({ children, color = "#787878", className = "", style }: BblLabelProps) {
  return (
    <span
      className={`text-[10px] font-medium uppercase tracking-[0.2em] ${className}`}
      style={{ color, fontFamily: "var(--font-sans)", ...style }}
    >
      {children}
    </span>
  );
}
