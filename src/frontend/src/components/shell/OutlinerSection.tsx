/**
 * Generic collapsible Outliner section — one per entity kind (orgs,
 * communities, factions). Purely presentational; the parent supplies the
 * list content as children.
 */

import { useState } from "react";

interface OutlinerSectionProps {
  title: string;
  count: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export function OutlinerSection({
  title,
  count,
  defaultOpen = true,
  children,
}: OutlinerSectionProps): React.JSX.Element {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section data-testid={`outliner-section-${title.toLowerCase()}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between border-b border-rebar py-1.5 text-left"
      >
        <span className="text-[10px] font-semibold uppercase tracking-widest text-fog">
          {title}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] text-ash">{count}</span>
          <span className="text-[9px] text-ash">{open ? "▼" : "▶"}</span>
        </span>
      </button>
      {open && <div className="flex flex-col gap-0.5 py-1.5">{children}</div>}
    </section>
  );
}
