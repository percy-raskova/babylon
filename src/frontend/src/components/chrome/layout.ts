/**
 * chrome/layout.ts — the single source of truth for cockpit chrome geometry
 * (spec-113 Phase V, owner-approved "layout SoT" fix).
 *
 * WHY THIS EXISTS. The cockpit paints two independent absolute-positioning
 * layers over the full-bleed map: the in-map control clusters (`MapControls`,
 * z-10) and the HUD rails (`FloatingPanel` instances — outliner / event tray /
 * objectives, z-20). Before this module each layer hard-coded the OTHER
 * layer's pixel widths as hand-tuned magic offsets, recorded only in comments
 * (`left-[250px] // clears the outliner`, `right-[300px] // clears the tray`).
 * Nothing tied the offset to the width it was clearing, so any width change —
 * or a control wide enough to overflow its anchor — silently drifted them into
 * overlap. That is a z-strata pointer-interception bug: a z-20 rail hit-tests
 * above a z-10 control, so the control stops taking clicks with no error and
 * no failing unit test (jsdom can't see pointer hit-testing). It recurred
 * three times in Phase V; the last was the grouped lens bar, anchored only by
 * its right edge, whose wrapping button row slid left underneath the outliner.
 *
 * THE RULE. Every rail declares its width HERE. Every map-control offset
 * DERIVES from these constants. The map controls are bounded to the
 * `MAP_SAFE_*` inset box — the region between the rails and below the top HUD
 * strip — so a wide, wrapping control can never reach a rail *by construction*,
 * not by a numeric coincidence that the next width tweak breaks.
 */

/** Left rail (`OutlinerOverlay`) open width, px. */
export const RAIL_LEFT_W = 240;
/** Left rail collapsed (icon-only) width, px. */
export const RAIL_LEFT_COLLAPSED_W = 44;
/** Right rail (`EventTray` / `ObjectivesTray`) width, px. */
export const RAIL_RIGHT_W = 280;
/** Right rail inset from the viewport's right edge, px (`AppShell`'s `right-2`). */
export const RAIL_RIGHT_INSET = 8;
/** Top HUD strip height, px (`FloatingPanel` anchor="top" TopBar band — `top-14`). */
export const HUD_TOP_H = 56;
/** Breathing gap between a rail edge and the map-safe area, px. */
export const GAP = 12;

/**
 * The map-control safe area: an inset box strictly between the two rails and
 * below the top HUD strip. `MapControls` bounds its clusters to this box so a
 * wide wrapping control (the grouped lens bar) wraps within it instead of
 * extending under a rail. Cleared against the OPEN left-rail width, so the
 * bound holds whether the outliner is open or collapsed (when collapsed the
 * controls simply gain unused headroom — never overlap).
 */
export const MAP_SAFE_LEFT = RAIL_LEFT_W + GAP; // 252
export const MAP_SAFE_RIGHT = RAIL_RIGHT_INSET + RAIL_RIGHT_W + GAP; // 300
export const MAP_SAFE_TOP = HUD_TOP_H; // 56

/**
 * CSS `max-width` for a right-anchored map-control cluster: the full safe-area
 * width. A right-anchored, content-sized cluster capped at this width can
 * extend left no further than `MAP_SAFE_LEFT`, so its wrapping content stops
 * exactly at the outliner's clearance — never under it.
 */
export const MAP_SAFE_MAX_WIDTH_CSS = `calc(100vw - ${MAP_SAFE_LEFT + MAP_SAFE_RIGHT}px)`;
