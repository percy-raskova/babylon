//! The ksbc [`StyleSheet`] for wiki markdown — Textual-parity, §9b tokens.
//!
//! `wiki_render` shipped M1–M3 on babylon-md's `DefaultStyleSheet` (stock
//! cyan headings, blue links, literal `#` markers and ``` fences) — the
//! "plain markdown" look the Director rejected at the M3 playtest. This
//! sheet restates what the LIVE Textual client actually renders under the
//! KSBC theme (`babylon.tui.theme.KSBC`: `primary=CRIMSON`), construct by
//! construct, using only [`crate::theme`] role tokens:
//!
//! - H1 crimson bold centered, H2 crimson underlined, H3 crimson bold
//!   (Textual `MarkdownH1..H3` under KSBC); H4–H6 follow Textual's
//!   foreground-toned ladder. NO literal `#` markers — Textual never shows
//!   Markdown punctuation.
//! - Inline code gold-on-recessed (Textual's `$warning`-wash under KSBC);
//!   block code a plain recessed band, NO ``` fences for anonymous blocks.
//! - Directive fences (`{statblock}`/`{absence}`/`{narrative}`) KEEP a
//!   `▌`-prefixed header line: their info string is player-facing content
//!   (Constitution III.11 — `{absence}` carries the honest-absence message
//!   itself), mirroring Textual's fence-widget headers. `{absence}` headers
//!   are crimson (the §9b absence-marker role); the rest gold.
//! - Bullets crimson (Textual's `$text-primary` bullet, saturated to the
//!   token — no pastel token exists in §9b).
//!
//! Wikilink gold/crimson styling stays in `wiki_render::restyle_link` (the
//! link side channel), NOT here — `link()` covers ordinary links only.
//! Cross-language color parity is guarded by
//! `tests/unit/render/test_rust_theme_parity.py` over [`crate::theme`].

use babylon_md::{AlertKind, StyleSheet};
use ratatui::layout::Alignment;
use ratatui::style::{Modifier, Style};

use crate::theme::{BONE, CRIMSON, DIM, GOLD, GREEN_DARK, MUTED_DARK, ROYAL};

/// The Babylon Archive wiki style sheet (see the module docs for the
/// construct-by-construct Textual parity mapping).
#[derive(Clone, Copy, Debug, Default)]
pub struct BabylonStyleSheet;

impl StyleSheet for BabylonStyleSheet {
    fn heading(&self, level: u8) -> Style {
        match level {
            1 => Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
            2 => Style::new().fg(CRIMSON).add_modifier(Modifier::UNDERLINED),
            3 => Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
            4 => Style::new()
                .fg(BONE)
                .add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
            5 => Style::new().fg(BONE).add_modifier(Modifier::BOLD),
            _ => Style::new().fg(DIM).add_modifier(Modifier::BOLD),
        }
    }

    fn heading_marker(&self, _level: u8) -> &str {
        ""
    }

    fn heading_alignment(&self, level: u8) -> Option<Alignment> {
        (level == 1).then_some(Alignment::Center)
    }

    fn code(&self) -> Style {
        Style::new().fg(GOLD).bg(MUTED_DARK)
    }

    fn code_block(&self) -> Style {
        Style::new().fg(BONE).bg(MUTED_DARK)
    }

    fn code_block_fence(&self, info: &str) -> &str {
        if info.is_empty() {
            ""
        } else {
            "▌"
        }
    }

    fn code_block_fence_close(&self, _info: &str) -> &str {
        ""
    }

    fn code_block_fence_style(&self, info: &str) -> Style {
        if info.starts_with("{absence}") {
            Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD)
        } else {
            Style::new().fg(GOLD).add_modifier(Modifier::BOLD)
        }
    }

    fn link(&self) -> Style {
        Style::new().fg(GOLD).add_modifier(Modifier::UNDERLINED)
    }

    fn blockquote(&self) -> Style {
        Style::new().fg(CRIMSON).add_modifier(Modifier::DIM)
    }

    fn metadata_block(&self) -> Style {
        Style::new().fg(DIM)
    }

    fn bullet_marker(&self) -> &str {
        "•"
    }

    fn list_marker_style(&self, _ordered: bool) -> Style {
        Style::new().fg(CRIMSON)
    }

    fn table_header(&self) -> Style {
        Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD)
    }

    fn table_border(&self) -> Style {
        Style::new().fg(DIM)
    }

    fn math_inline(&self) -> Style {
        Style::new().fg(GOLD).add_modifier(Modifier::ITALIC)
    }

    fn math_display(&self) -> Style {
        Style::new().fg(GOLD)
    }

    fn html(&self) -> Style {
        Style::new().fg(DIM)
    }

    fn footnote_ref(&self) -> Style {
        Style::new().fg(DIM).add_modifier(Modifier::ITALIC)
    }

    fn footnote_def(&self) -> Style {
        Style::new().fg(DIM)
    }

    fn alert(&self, kind: AlertKind) -> Style {
        match kind {
            AlertKind::Note => Style::new().fg(ROYAL),
            AlertKind::Tip => Style::new().fg(GREEN_DARK),
            AlertKind::Important | AlertKind::Warning => Style::new().fg(GOLD),
            AlertKind::Caution => Style::new().fg(CRIMSON),
        }
    }

    fn image_alt(&self) -> Style {
        Style::new().fg(DIM).add_modifier(Modifier::ITALIC)
    }
}
