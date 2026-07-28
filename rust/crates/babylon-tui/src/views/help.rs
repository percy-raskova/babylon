//! The `?` help overlay (Wave 1 contract §3, defect D2).
//!
//! **RECORDED DEVIATION from the master plan's wording** ("a view-stack
//! entry"): the as-built overlay pattern is the PALETTE FIELD —
//! `Option<PaletteView>` on `App`, intercepting keys first and rendering
//! last over the base layout — and this view follows that precedent
//! exactly. The view stack only ever holds Lobby/Wiki (the M2 port
//! deliberately dissolved stacked chrome).
//!
//! Content: the ACTIVE surface's bindings first (mode-scoped — the same
//! [`KeybarSurface`] the keybar reads), then every other section, all
//! from [`crate::views::keybar::help_sections`] — one source of truth,
//! so the keybar and the help screen cannot drift apart.

use ratatui::layout::Rect;
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Clear, Paragraph};
use ratatui::Frame;

use crate::theme::{BONE, CRIMSON, DIM, GOLD};
use crate::views::keybar::{help_sections, KeybarSurface};

/// The modal help overlay's own state: just the scroll offset.
#[derive(Debug, Default)]
pub struct HelpView {
    scroll: u16,
}

/// What a help keypress asks the shell to do.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HelpAction {
    /// Close the overlay.
    Close,
    /// Consumed internally (scroll) — nothing for the shell to do.
    Handled,
}

impl HelpView {
    /// Handle a key while the overlay is open (modal: the shell routes
    /// every key here first, the palette precedent).
    pub fn handle_key(&mut self, code: ratatui::crossterm::event::KeyCode) -> HelpAction {
        use ratatui::crossterm::event::KeyCode;
        match code {
            KeyCode::Esc | KeyCode::Char('?') | KeyCode::Char('q') => HelpAction::Close,
            KeyCode::Up => {
                self.scroll = self.scroll.saturating_sub(1);
                HelpAction::Handled
            }
            KeyCode::Down => {
                self.scroll = self.scroll.saturating_add(1);
                HelpAction::Handled
            }
            KeyCode::PageUp => {
                self.scroll = self.scroll.saturating_sub(10);
                HelpAction::Handled
            }
            KeyCode::PageDown => {
                self.scroll = self.scroll.saturating_add(10);
                HelpAction::Handled
            }
            _ => HelpAction::Handled,
        }
    }

    /// Render the centered plate (newt idiom: hard border in CRIMSON —
    /// the peek overlay precedent — title tab, field-colored interior),
    /// the active surface's section first.
    pub fn render(&self, frame: &mut Frame<'_>, area: Rect, active: KeybarSurface) {
        let width = area.width.min(72);
        let height = area.height.min(26);
        let plate = Rect {
            x: area.x + (area.width.saturating_sub(width)) / 2,
            y: area.y + (area.height.saturating_sub(height)) / 2,
            width,
            height,
        };
        frame.render_widget(Clear, plate);
        let block = Block::bordered()
            .title(" THE ARCHIVE — BINDINGS (Esc closes) ")
            .border_style(Style::new().fg(CRIMSON));
        let inner = block.inner(plate);
        frame.render_widget(block, plate);

        let mut lines: Vec<Line<'static>> = Vec::new();
        let sections = help_sections();
        let mut ordered: Vec<&(&'static str, KeybarSurface, Vec<crate::views::keybar::Hint>)> =
            sections.iter().filter(|(_, s, _)| *s == active).collect();
        ordered.extend(sections.iter().filter(|(_, s, _)| *s != active));
        for (title, surface, hints) in ordered {
            let marker = if *surface == active {
                " ◄ you are here"
            } else {
                ""
            };
            lines.push(Line::from(vec![
                Span::styled(
                    (*title).to_string(),
                    Style::new().fg(GOLD).add_modifier(Modifier::BOLD),
                ),
                Span::styled(marker.to_string(), Style::new().fg(CRIMSON)),
            ]));
            for h in hints {
                lines.push(Line::from(vec![
                    Span::styled(format!("  {:<10}", h.key), Style::new().fg(GOLD)),
                    Span::styled(h.label.to_string(), Style::new().fg(BONE)),
                ]));
            }
            lines.push(Line::from(Span::styled(
                String::new(),
                Style::new().fg(DIM),
            )));
        }
        let max_scroll = (lines.len() as u16).saturating_sub(inner.height);
        frame.render_widget(
            Paragraph::new(lines).scroll((self.scroll.min(max_scroll), 0)),
            inner,
        );
    }
}
