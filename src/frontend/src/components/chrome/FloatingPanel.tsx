/**
 * FloatingPanel — the one primitive every chrome overlay instances
 * (architecture §0/§1.3). Skinned to the Installer/newt dialog anatomy
 * (DESIGN_BIBLE.md §9b, spec-113 Lane SKIN-CHROME): plate background over
 * the live map (`bg-plate/85` + `backdrop-blur-sm`, small panels only —
 * bible's "in-game floating chrome... same anatomy at reduced opacity"),
 * square corners, hard zero-blur offset shadow, and a title tab that
 * BREAKS the top border (fieldset/legend idiom, crimson mono uppercase)
 * instead of sitting inside a bordered header strip.
 *
 * "Structure now, skin later" (architecture §0): every chrome component is
 * an instance of this primitive so the Design Bible's later token/visual
 * pass never touches call sites, only this file and `index.css`. The
 * props contract (anchor/collapsed/onToggle/width/testId/children) is
 * frozen — this is a restyle, not an interface change.
 *
 * Children stay mounted in the DOM even while `collapsed` — visibility is
 * CSS-only (`hidden`), never a JSX unmount — because several hosted panels
 * (BottomDrawer/TimeseriesChart, EventTray/EventsFeed) must keep their
 * tick fan-out alive while visually hidden (the same rule the legacy
 * `BottomStrip` enforced).
 *
 * No drag in v1 — the `anchor` enum is the extension point the Design
 * Bible amends later (architecture §1.3).
 */

import { keyButtonClass } from "./installerKit";

interface FloatingPanelProps {
  title?: string;
  anchor: "left" | "right" | "bottom" | "top" | "free";
  collapsed?: boolean;
  onToggle?: () => void;
  width?: number;
  children: React.ReactNode;
  testId: string;
}

const ANCHOR_CLASSES: Record<FloatingPanelProps["anchor"], string> = {
  // left/right rails start at top-14, BELOW the anchor="top" HUD strip —
  // at top-0 the outliner buried the TopBar's left segment (Phase V live
  // finding); 14 matches AppShell's right-rail offset for the same reason.
  left: "absolute left-0 top-14 bottom-0 border-r",
  right: "absolute right-0 top-14 bottom-0 border-l",
  top: "absolute inset-x-0 top-0 border-b",
  bottom: "absolute inset-x-0 bottom-0 border-t",
  free: "relative",
};

export function FloatingPanel({
  title,
  anchor,
  collapsed = false,
  onToggle,
  width,
  children,
  testId,
}: FloatingPanelProps): React.JSX.Element {
  const hasHeader = title !== undefined || onToggle !== undefined;

  return (
    <div
      data-testid={testId}
      className={`pointer-events-auto flex flex-col overflow-hidden rounded-none border-2 border-ksbc-muted-1 bg-plate/85 pt-2 shadow-[6px_6px_0_#000] backdrop-blur-sm ${ANCHOR_CLASSES[anchor]}`}
      style={width !== undefined ? { width } : undefined}
    >
      {hasHeader && (
        <div className="relative -mt-2 mb-1 flex shrink-0 items-center justify-between gap-2 px-2">
          {title !== undefined && (
            <span className="-mt-[9px] w-fit bg-plate px-1.5 font-mono text-[10px] uppercase tracking-widest text-accent-crimson">
              {title}
            </span>
          )}
          {onToggle !== undefined && (
            <button
              onClick={onToggle}
              aria-expanded={!collapsed}
              className={keyButtonClass(false, "-mt-[9px] px-1.5 py-0 text-[10px] leading-none")}
            >
              {collapsed ? "▸" : "▾"}
            </button>
          )}
        </div>
      )}
      <div className={`min-h-0 flex-1 overflow-y-auto ${collapsed ? "hidden" : ""}`}>
        {children}
      </div>
    </div>
  );
}
