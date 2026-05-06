/**
 * PageHeader — consistent page header used by every in-game route.
 *
 * Displays title, optional subtitle, breadcrumb trail, and right slot.
 */

import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: string[];
  right?: ReactNode;
}

export function PageHeader({ title, subtitle, breadcrumbs, right }: PageHeaderProps) {
  return (
    <div className="flex shrink-0 items-start justify-between border-b border-soot px-4 py-3">
      <div className="flex flex-col gap-1">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <div className="flex items-center gap-1 text-[9px] uppercase tracking-[0.2em] text-ash">
            {breadcrumbs.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1">
                {i > 0 && <span className="text-chassis">›</span>}
                <span className={i === breadcrumbs.length - 1 ? "text-gold" : ""}>{crumb}</span>
              </span>
            ))}
          </div>
        )}
        <h1 className="text-lg font-semibold text-bone">{title}</h1>
        {subtitle && <p className="text-[11px] leading-snug text-ash">{subtitle}</p>}
      </div>
      {right && <div className="shrink-0 pt-1">{right}</div>}
    </div>
  );
}
