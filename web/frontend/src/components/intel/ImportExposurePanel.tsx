/**
 * ImportExposurePanel — import-exposure provenance breakdown for Territory Detail.
 * Spec 103 FR-103-11: renders a drill-down chain ending at reference-data
 * citations. Uses Cold Collapse tokens. The drill-down is click-to-expand
 * (state-based disclosure), reusing the BreakdownTree visual pattern.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { BblPanel } from "@/components/bbl";
import { useCountyExposure } from "@/hooks/useCountyExposure";
import type { Contributor, Citation } from "@/types/trade";
import "@/components/intel/import-exposure.css";

interface Props {
  gameId: string | null;
  countyFips: string | null;
}

function sourceIcon(kind: string): string {
  if (kind === "reference_table") return "📚";
  if (kind === "dynamic_table") return "📊";
  return "🔗";
}

function ContributorRow({ contributor, depth }: { contributor: Contributor; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = contributor.children.length > 0;

  return (
    <li className="exposure-contributor" style={{ paddingLeft: depth > 0 ? "0.75rem" : 0 }}>
      <div
        className="exposure-contributor-row"
        onClick={() => hasChildren && setExpanded(!expanded)}
        role={hasChildren ? "button" : undefined}
      >
        <span className={depth === 0 ? "exposure-label-top" : "exposure-label-sub"}>
          {hasChildren && <span className="exposure-toggle">{expanded ? "\u25be" : "\u25b8"}</span>}
          {contributor.label}
        </span>
        <div className="exposure-values">
          <span className={contributor.value < 0 ? "text-crimson" : "text-bone"}>
            {contributor.value.toFixed(2)}
          </span>
          {depth === 0 && (
            <span className="exposure-share">({(contributor.share * 100).toFixed(0)}%)</span>
          )}
        </div>
      </div>
      <div className="exposure-source">
        {sourceIcon(contributor.source.kind)} {contributor.source.path}
      </div>
      {hasChildren && expanded && (
        <ul className="exposure-children">
          {contributor.children.map((child, i) => (
            <ContributorRow key={`${child.label}-${i}`} contributor={child} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="exposure-citations">
      <div className="wire-label exposure-citations-label">Reference Data</div>
      <ul className="exposure-citation-list">
        {citations.map((cite) => (
          <li key={cite.id} className="exposure-citation">
            <span className="exposure-cite-source">{cite.source}</span>
            <span className="exposure-cite-table" style={{ fontFamily: "var(--font-mono)" }}>
              {cite.table}
            </span>
            {cite.year !== undefined && <span className="exposure-cite-year">{cite.year}</span>}
            {cite.notes && <span className="exposure-cite-notes">{cite.notes}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ImportExposurePanel({ gameId, countyFips }: Props) {
  const { data, loading, error } = useCountyExposure(gameId, countyFips);

  let body: ReactNode;
  if (loading && data.has_data === false) {
    body = <div className="text-[11px] text-ash">Loading exposure data...</div>;
  } else if (error) {
    body = (
      <div className="text-[11px]" style={{ color: "var(--babylon-laser)" }}>
        Error: {error}
      </div>
    );
  } else if (!data.has_data) {
    body = (
      <div className="text-[11px] text-ash">
        No import-exposure data yet for this county. Exposure populates when the engine emits
        boundary flows and spec-100 weights are loaded.
      </div>
    );
  } else {
    body = (
      <div className="exposure-body">
        <div className="exposure-total">
          <span className="wire-label">Total Exposure</span>
          <span
            className="text-[18px] font-bold"
            style={{ color: "var(--babylon-bone)", fontFamily: "var(--font-mono)" }}
          >
            {data.total_exposure.toFixed(2)}
          </span>
        </div>
        <ul className="exposure-contributors">
          {data.breakdown.contributors.map((c, i) => (
            <ContributorRow key={`${c.label}-${i}`} contributor={c} depth={0} />
          ))}
        </ul>
        <CitationList citations={data.citations} />
      </div>
    );
  }

  return (
    <BblPanel title="Import Exposure" accent="#5fbf7a">
      {body}
    </BblPanel>
  );
}
