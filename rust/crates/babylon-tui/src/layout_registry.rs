//! Per-frame widget-id → screen-area → entity registry (the hover/peek
//! foundation, plan Task 14).
//!
//! Every view render pass registers the screen [`Rect`] of anything a mouse
//! move or click should resolve against (a wikilink span, a stat-plate row,
//! a map hex). [`LayoutRegistry::hit`] then answers "what's under this
//! point" for `App::handle_mouse` to route into a hover-peek or a click
//! navigation. The registry is rebuilt every frame — [`LayoutRegistry::clear`]
//! is called once at the top of each render pass, then every widget that
//! wants to be hit-testable calls [`LayoutRegistry::register`] as it draws.
//! Mouse is a convenience path only (design R1: ratatui#1227 leaves OSC 8
//! hyperlinks unavailable, so hover/click both go through this registry
//! rather than terminal-native links); keyboard navigation never depends on
//! it.
//!
//! **Innermost-wins hit testing.** Widgets nest (a wikilink span sits inside
//! a wiki-page paragraph, which sits inside the page viewport); a hit test
//! must resolve to the smallest registered area containing the point, not
//! whichever was registered first or drawn outermost. Ties (two rects of
//! identical area both containing the point — e.g. two links stacked at
//! the same coordinates across a jumplist transition) resolve to whichever
//! was **registered last**, so a widget re-registering itself after an
//! earlier stale entry always wins.

use ratatui::layout::Rect;

/// Opaque identifier for a registered widget/span.
///
/// Callers mint their own ids (a wikilink index, a stat-row index, a hex
/// coordinate encoded as an integer); the registry never interprets it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WidgetId(pub u32);

/// One frame's worth of hit-testable screen areas.
///
/// Cleared and rebuilt every render pass (see the module docs);
/// [`LayoutRegistry::hit`] never mutates it, so a hover/click frame can
/// query it as many times as it needs without side effects.
#[derive(Debug, Default)]
pub struct LayoutRegistry {
    rects: Vec<(WidgetId, Rect, Option<String>)>,
}

/// Returns `true` when `(col, row)` falls inside `area`.
///
/// A zero-width or zero-height `area` contains no point (Rect's own
/// invariant: `x + width` and `y + height` are exclusive upper bounds).
fn contains(area: Rect, col: u16, row: u16) -> bool {
    let within_columns = col >= area.x && col < area.x.saturating_add(area.width);
    let within_rows = row >= area.y && row < area.y.saturating_add(area.height);
    within_columns && within_rows
}

/// `area`'s cell count as `u32` (max `u16::MAX * u16::MAX` fits `u32`
/// without overflow), used only to compare "smaller area" for the
/// innermost-wins rule — never printed or serialized.
fn cell_count(area: Rect) -> u32 {
    u32::from(area.width) * u32::from(area.height)
}

impl LayoutRegistry {
    /// A fresh, empty registry.
    pub fn new() -> Self {
        Self { rects: Vec::new() }
    }

    /// Drop every registered rect — call once at the top of each frame's
    /// render pass, before any widget registers itself for this frame.
    pub fn clear(&mut self) {
        self.rects.clear();
    }

    /// Register `area` as hit-testable, tagged with `id` and an optional
    /// navigation target (`entity`, e.g. a `babylon://` subject id).
    ///
    /// Registration order matters only for tie-breaking (see the module
    /// docs' "ties resolve to last registered" rule) — otherwise later
    /// calls neither shadow nor depend on earlier ones.
    pub fn register(&mut self, id: WidgetId, area: Rect, entity: Option<String>) {
        self.rects.push((id, area, entity));
    }

    /// Resolve the point `(col, row)` to the innermost registered rect that
    /// contains it, or `None` if nothing was registered there.
    ///
    /// "Innermost" means smallest cell count; a tie between two equally
    /// small containing rects goes to whichever was registered later (a
    /// single linear scan with a `<=` comparison against the current best
    /// gives exactly that — no separate tie-break pass is needed).
    pub fn hit(&self, col: u16, row: u16) -> Option<&(WidgetId, Rect, Option<String>)> {
        let mut best: Option<(usize, u32)> = None;
        for (index, (_, area, _)) in self.rects.iter().enumerate() {
            if !contains(*area, col, row) {
                continue;
            }
            let size = cell_count(*area);
            let is_better = match best {
                None => true,
                Some((_, best_size)) => size <= best_size,
            };
            if is_better {
                best = Some((index, size));
            }
        }
        best.map(|(index, _)| &self.rects[index])
    }
}

// Contract tests (nested/tie/miss/clear) live in `tests/layout_registry.rs`
// as an integration suite over this module's public API only.
