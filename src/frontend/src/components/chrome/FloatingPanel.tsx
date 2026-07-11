/**
 * FloatingPanel — the one primitive every chrome overlay instances
 * (architecture §0/§1.3). Renders a concrete/rebar-bordered panel with
 * backdrop-blur over the map, promoting the `bg-void/80 backdrop-blur-sm`
 * idiom `DeckGLMap`'s control cluster already used into a shared,
 * theme-token-backed component (`index.css`'s additive `--chrome-*`
 * tokens).
 *
 * "Structure now, skin later" (architecture §0): every chrome component is
 * an instance of this primitive so the Design Bible's later token/visual
 * pass never touches call sites, only this file and `index.css`.
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
  left: "absolute left-0 top-0 bottom-0 border-r",
  right: "absolute right-0 top-0 bottom-0 border-l",
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
      className={`pointer-events-auto flex flex-col overflow-hidden border-chrome-border bg-chrome-bg backdrop-blur-sm shadow-[var(--chrome-shadow)] ${ANCHOR_CLASSES[anchor]}`}
      style={width !== undefined ? { width } : undefined}
    >
      {hasHeader && (
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-rebar px-2 py-1.5">
          {title !== undefined && (
            <span className="text-[10px] font-semibold uppercase tracking-widest text-fog">
              {title}
            </span>
          )}
          {onToggle !== undefined && (
            <button
              onClick={onToggle}
              aria-expanded={!collapsed}
              className="rounded border border-rebar px-1.5 py-0.5 text-[10px] text-fog hover:border-spire hover:text-spire"
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
