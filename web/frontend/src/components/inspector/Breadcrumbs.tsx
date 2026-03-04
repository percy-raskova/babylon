/**
 * Breadcrumbs — drill-down navigation stack for the inspector panel.
 *
 * Renders the breadcrumb stack from uiStore as clickable chips:
 * Overview > Territory Name > Org Name
 */

import { useUIStore } from "@/stores/uiStore";

export function Breadcrumbs() {
  const breadcrumbs = useUIStore((s) => s.breadcrumbs);
  const popBreadcrumbTo = useUIStore((s) => s.popBreadcrumbTo);
  const clearBreadcrumbs = useUIStore((s) => s.clearBreadcrumbs);
  const setSelectedHex = useUIStore((s) => s.setSelectedHex);
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);

  if (breadcrumbs.length === 0) return null;

  const handleOverviewClick = () => {
    clearBreadcrumbs();
    setSelectedHex(null);
    setSelectedNode(null);
  };

  const handleCrumbClick = (index: number) => {
    if (index === -1) {
      handleOverviewClick();
      return;
    }
    popBreadcrumbTo(index);
    const crumb = breadcrumbs[index];
    if (crumb) {
      if (crumb.entityType === "territory") {
        setSelectedHex(crumb.entityId);
        setSelectedNode(null);
      } else if (crumb.entityType !== "overview") {
        setSelectedNode(crumb.entityId);
      }
    }
  };

  return (
    <nav
      className="flex items-center gap-1 border-b border-soot px-3 py-1.5"
      aria-label="Breadcrumb"
    >
      <button
        onClick={handleOverviewClick}
        className="text-[11px] text-ash transition-colors hover:text-gold"
      >
        Overview
      </button>
      {breadcrumbs.map((crumb, i) => (
        <span key={crumb.entityId ?? i} className="flex items-center gap-1">
          <span className="text-[10px] text-wet-concrete">/</span>
          {i < breadcrumbs.length - 1 ? (
            <button
              onClick={() => handleCrumbClick(i)}
              className="text-[11px] text-silver transition-colors hover:text-gold"
            >
              {crumb.displayName}
            </button>
          ) : (
            <span className="text-[11px] font-medium text-bone">{crumb.displayName}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
