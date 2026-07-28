//! The persistent one-line keybar (Wave 1 contract §2, defect D1).
//!
//! Content is CONTEXT-AWARE: a pure function of the active surface — the
//! htop/Midnight-Commander pattern, ksbc-styled (GOLD key glyphs, BONE
//! action labels, DIM separators on the near-black field). Single-key
//! hints are CLICKABLE: each registers into the per-frame
//! [`LayoutRegistry`] as `key:{name}` (the `verb:{slot}` precedent) and
//! `App::handle_mouse` routes a hit through the SAME `handle_key` path
//! the keyboard uses — one routing authority, never a second dispatch
//! table. Composite hints (`↑↓`, `[ ]`) render unregistered: there is no
//! single key event a click could honestly synthesize.

use ratatui::layout::Rect;
use ratatui::style::Style;
use ratatui::text::{Line, Span};
use ratatui::Frame;

use crate::layout_registry::{LayoutRegistry, WidgetId};
use crate::theme::{BONE, DIM, GOLD};

/// One keybar hint: the display glyph, the action label, and — for
/// single-key hints — the `key_event_from_name` name a click dispatches
/// (`None` = display-only, unclickable).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Hint {
    /// The key glyph shown (e.g. `"Tab"`, `"g"`, `"↑↓"`).
    pub key: &'static str,
    /// The short action label (e.g. `"focus"`, `"kind"`).
    pub label: &'static str,
    /// The dispatchable key name, when one key honestly maps.
    pub dispatch: Option<&'static str>,
}

const fn hint(key: &'static str, label: &'static str, dispatch: Option<&'static str>) -> Hint {
    Hint {
        key,
        label,
        dispatch,
    }
}

/// The surface the keybar describes — derived by the app shell from
/// `(views.last, chrome{focus, pane, topology mode}, palette open)`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeybarSurface {
    /// The lobby root.
    Lobby,
    /// Play chrome, wiki pane, center focused.
    Wiki,
    /// Play chrome, topology pane, glyph floor.
    TopologyGlyph,
    /// Play chrome, topology pane, a 3D mode.
    Topology3d,
    /// Play chrome, map pane (M5 contract §3).
    Map,
    /// Play chrome, the dashboard absence fence (map fell to M5).
    AbsencePane,
    /// A rail holds focus (`watchlist` distinguishes the `p` pin hint).
    Rail {
        /// `true` = the watchlist rail (which adds `p pin`).
        watchlist: bool,
    },
    /// A modal overlay (palette) is open and intercepting keys.
    Overlay,
    /// The chrome-less failure wiki page.
    BareWiki,
}

/// The trailing cluster every surface shares.
const GLOBAL_TAIL: &[Hint] = &[
    hint("?", "help", Some("?")),
    hint("/", "palette", Some("/")),
    hint("q", "back", Some("q")),
];

/// The surface-specific hint set, leading cluster first (contract §2's
/// per-surface table verbatim).
pub fn hints(surface: KeybarSurface) -> Vec<Hint> {
    let lead: &[Hint] = match surface {
        KeybarSurface::Lobby => &[
            hint("↑↓", "select", None),
            hint("Enter", "load", Some("enter")),
            hint("n", "new", Some("n")),
        ],
        KeybarSurface::Wiki => &[
            hint("[ ]", "jumps", None),
            hint("n/p", "links", None),
            hint("Enter", "open", Some("enter")),
            hint("K", "peek", Some("K")),
            hint("1-4", "panes", None),
            hint("Tab", "focus", Some("tab")),
        ],
        KeybarSurface::TopologyGlyph => &[
            hint("g", "kind", Some("g")),
            hint("s", "3D", Some("s")),
            hint("↑↓", "scroll", None),
            hint("Esc", "wiki", Some("esc")),
        ],
        KeybarSurface::Topology3d => &[
            hint("←→↑↓", "rotate", None),
            hint("+/-", "zoom", None),
            hint("0", "reset", Some("0")),
            hint("s", "mode", Some("s")),
            hint("f", "field", Some("f")),
            hint("g", "glyph", Some("g")),
            hint("Esc", "wiki", Some("esc")),
        ],
        KeybarSurface::Map => &[
            hint("l", "lens", Some("l")),
            hint("y", "tier", Some("y")),
            hint("+/-", "zoom", None),
            hint("←→↑↓", "pan", None),
            hint("0", "reset", Some("0")),
            hint("Esc", "wiki", Some("esc")),
        ],
        KeybarSurface::AbsencePane => &[
            hint("1-4", "panes", None),
            hint("Tab", "focus", Some("tab")),
        ],
        KeybarSurface::Rail { watchlist: true } => &[
            hint("↑↓", "rows", None),
            hint("Enter", "open", Some("enter")),
            hint("p", "pin", Some("p")),
            hint("Esc", "center", Some("esc")),
        ],
        KeybarSurface::Rail { watchlist: false } => &[
            hint("↑↓", "rows", None),
            hint("Enter", "open", Some("enter")),
            hint("Esc", "center", Some("esc")),
        ],
        KeybarSurface::Overlay => &[
            hint("↑↓", "match", None),
            hint("Enter", "open", Some("enter")),
            hint("Esc", "close", Some("esc")),
        ],
        KeybarSurface::BareWiki => &[hint("↑↓", "scroll", None), hint("q", "back", Some("q"))],
    };
    let mut all = lead.to_vec();
    // The overlay's own close set IS its tail; everywhere else the global
    // trio applies (BareWiki already leads with q).
    if !matches!(surface, KeybarSurface::Overlay | KeybarSurface::BareWiki) {
        all.extend_from_slice(GLOBAL_TAIL);
    }
    all
}

/// The full, help-screen-tier binding sections (Wave 1 contract §3):
/// each surface's KEYBAR hints first (one source of truth — the keybar
/// and the help screen cannot drift apart), then the surface's
/// full-detail rows the one-line keybar has no room for. Global
/// bindings get their own section.
pub fn help_sections() -> Vec<(&'static str, KeybarSurface, Vec<Hint>)> {
    let extend = |surface: KeybarSurface, extra: &[Hint]| {
        let mut all = hints(surface);
        all.extend_from_slice(extra);
        all
    };
    vec![
        (
            "LOBBY",
            KeybarSurface::Lobby,
            extend(KeybarSurface::Lobby, &[hint("j/k", "select (vi)", None)]),
        ),
        (
            "WIKI PANE",
            KeybarSurface::Wiki,
            extend(
                KeybarSurface::Wiki,
                &[
                    hint("Ctrl-O/I", "jump back / forward (aliases)", None),
                    hint("PgUp/PgDn", "scroll a page", None),
                    hint("↑↓", "scroll a row", None),
                    hint("P", "pin dossier to watchlist", None),
                    hint("t", "advance a tick", None),
                    hint("r", "run until autopause", None),
                    hint("a", "acknowledge the pause", None),
                    hint("F1-F9", "issue the verb slot", None),
                    hint("Esc", "back (dossier root leaves campaign)", None),
                ],
            ),
        ),
        (
            "TOPOLOGY — GLYPH FLOOR",
            KeybarSurface::TopologyGlyph,
            hints(KeybarSurface::TopologyGlyph),
        ),
        (
            "TOPOLOGY — 3D",
            KeybarSurface::Topology3d,
            hints(KeybarSurface::Topology3d),
        ),
        (
            "MAP",
            KeybarSurface::Map,
            extend(
                KeybarSurface::Map,
                &[hint("wheel", "zoom at the cursor region", None)],
            ),
        ),
        (
            "DASHBOARD",
            KeybarSurface::AbsencePane,
            hints(KeybarSurface::AbsencePane),
        ),
        (
            "WATCHLIST RAIL",
            KeybarSurface::Rail { watchlist: true },
            hints(KeybarSurface::Rail { watchlist: true }),
        ),
        (
            "CHRONICLE RAIL",
            KeybarSurface::Rail { watchlist: false },
            hints(KeybarSurface::Rail { watchlist: false }),
        ),
        (
            "PALETTE",
            KeybarSurface::Overlay,
            extend(
                KeybarSurface::Overlay,
                &[hint("type", "filter subjects", None)],
            ),
        ),
        (
            "EVERYWHERE",
            KeybarSurface::BareWiki,
            vec![
                hint("?", "this help", None),
                hint("/", "command palette", None),
                hint("Tab/S-Tab", "cycle focus fwd / back", None),
                hint("1-4", "dashboard / map / wiki / topology", None),
                hint("K", "cycle peek depth", None),
                hint("q", "back / quit at the lobby", None),
            ],
        ),
    ]
}

/// Widget-id base for keybar cells (the `verb:` rows use 1000+; keybar
/// takes 2000+ — ids only need to be frame-unique for the registry).
const KEYBAR_ID_BASE: u32 = 2000;

/// Render the keybar into its one-line band, registering each
/// dispatchable cell as `key:{name}`.
pub fn render_keybar(
    frame: &mut Frame<'_>,
    area: Rect,
    surface: KeybarSurface,
    registry: &mut LayoutRegistry,
) {
    if area.height == 0 {
        return;
    }
    let mut spans: Vec<Span<'static>> = Vec::new();
    let mut col = area.x;
    for (idx, h) in hints(surface).into_iter().enumerate() {
        if idx > 0 {
            let sep = " · ";
            spans.push(Span::styled(sep, Style::new().fg(DIM)));
            col += sep.chars().count() as u16;
        }
        let cell_start = col;
        spans.push(Span::styled(h.key, Style::new().fg(GOLD)));
        col += h.key.chars().count() as u16;
        spans.push(Span::styled(" ", Style::new()));
        col += 1;
        spans.push(Span::styled(h.label, Style::new().fg(BONE)));
        col += h.label.chars().count() as u16;
        if let Some(name) = h.dispatch {
            let width = col.saturating_sub(cell_start);
            if cell_start < area.x + area.width {
                registry.register(
                    WidgetId(KEYBAR_ID_BASE + idx as u32),
                    Rect {
                        x: cell_start,
                        y: area.y,
                        width: width.min((area.x + area.width).saturating_sub(cell_start)),
                        height: 1,
                    },
                    Some(format!("key:{name}")),
                );
            }
        }
    }
    frame.render_widget(Line::from(spans), area);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_surface_has_hints_and_a_back_affordance() {
        for surface in [
            KeybarSurface::Lobby,
            KeybarSurface::Wiki,
            KeybarSurface::TopologyGlyph,
            KeybarSurface::Topology3d,
            KeybarSurface::Map,
            KeybarSurface::AbsencePane,
            KeybarSurface::Rail { watchlist: true },
            KeybarSurface::Rail { watchlist: false },
            KeybarSurface::Overlay,
            KeybarSurface::BareWiki,
        ] {
            let hs = hints(surface);
            assert!(!hs.is_empty(), "{surface:?} has no hints");
            assert!(
                hs.iter().any(|h| h.key == "q" || h.key == "Esc"),
                "{surface:?} has no back/close affordance"
            );
        }
    }

    #[test]
    fn dispatchable_hints_use_known_key_names() {
        // Every dispatch name must resolve through key_event_from_name —
        // a typo here would make the click a silent no-op.
        for surface in [
            KeybarSurface::Lobby,
            KeybarSurface::Wiki,
            KeybarSurface::TopologyGlyph,
            KeybarSurface::Topology3d,
            KeybarSurface::Map,
            KeybarSurface::AbsencePane,
            KeybarSurface::Rail { watchlist: true },
            KeybarSurface::Overlay,
            KeybarSurface::BareWiki,
        ] {
            for h in hints(surface) {
                if let Some(name) = h.dispatch {
                    assert!(
                        crate::app::key_event_from_name(name).is_some(),
                        "{surface:?}: dispatch name {name:?} is unknown to key_event_from_name"
                    );
                }
            }
        }
    }

    #[test]
    fn watchlist_rail_gains_the_pin_hint() {
        assert!(hints(KeybarSurface::Rail { watchlist: true })
            .iter()
            .any(|h| h.label == "pin"));
        assert!(!hints(KeybarSurface::Rail { watchlist: false })
            .iter()
            .any(|h| h.label == "pin"));
    }
}
