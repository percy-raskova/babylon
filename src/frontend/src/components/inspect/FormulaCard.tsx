/**
 * FormulaCard — renders one resolved `InspectionNode`'s sections
 * (architecture.md §2.1: "terminal frame for a formula: expression,
 * per-input rows, constants with provenance note").
 *
 * DESIGN_BIBLE.md §4's "one fixed card layout shell across all depth
 * levels" (Tufte VDQI: country → region → county → hex reuse one card
 * anatomy, only data changes) means this same section/row renderer backs
 * EVERY resolved node — entity frames (hex/org/node/edge/community) and
 * formula frames (metric/formula) alike, since both resolve to the exact
 * same `{sections: InspectionSection[]}` shape (`lib/inspect/adapters/*`).
 * The name follows architecture.md's component list; the implementation
 * is intentionally the one generic shell, not a formula-specific fork.
 */

import type { InspectionNode, InspectionRef } from "@/types/inspection";
import { ValueRow } from "./ValueRow";

interface FormulaCardProps {
  node: InspectionNode;
  canDrill: boolean;
  onDrill: (ref: InspectionRef) => void;
}

export function FormulaCard({ node, canDrill, onDrill }: FormulaCardProps): React.JSX.Element {
  return (
    <div className="flex flex-col gap-2" data-testid="formula-card">
      {node.sections.map((section, i) => (
        <div key={section.label ?? `section-${i}`} className="flex flex-col gap-0.5">
          {section.label !== undefined && (
            <span className="text-[9px] uppercase tracking-widest text-ash">{section.label}</span>
          )}
          {section.rows.map((row) => (
            <ValueRow key={row.label} row={row} canDrill={canDrill} onDrill={onDrill} />
          ))}
        </div>
      ))}
    </div>
  );
}
