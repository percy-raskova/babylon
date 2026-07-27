//! The lobby view: the campaign load/new menu (M1 Task 16).
//!
//! Mirrors `babylon.tui.campaign_menu`'s `LobbyScreen` framing and display
//! fields over the wire shape `Host::lobby_catalog_json` actually serves
//! (`src/babylon/tui/host.py::RustClientHost.lobby_catalog_json`):
//! `campaign_id`, `name`, `tick`, `status`, `defines_hash`, `engine_version`.
//! An empty catalog renders the honest-absence body used by the M0
//! hello-frame (Constitution III.11), never a fabricated row.

use ratatui::crossterm::event::KeyCode;
use ratatui::layout::Rect;
use ratatui::style::{Modifier, Style};
use ratatui::widgets::{Block, List, ListItem, ListState, Paragraph};
use ratatui::Frame;
use serde::Deserialize;

use crate::views::msg::AppEvent;

/// The lobby's idle title, mirroring `LobbyScreen.compose`'s
/// `Label("THE ARCHIVE — CAMPAIGNS")`.
const LOBBY_TITLE: &str = "THE ARCHIVE — CAMPAIGNS";

/// The honest-absence body for an empty catalog (mirrors the M0 hello-frame).
const EMPTY_BODY: &str = "No campaigns in the catalog.";

/// One lobby catalog row as served by `Host::lobby_catalog_json`.
///
/// Field shape pins to `RustClientHost.lobby_catalog_json`'s emitted keys —
/// see `src/babylon/tui/host.py`.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct LobbyRow {
    /// The campaign's UUID, as a string (never parsed to a UUID type here —
    /// it round-trips opaquely into `AppEvent::LoadCampaign`).
    pub campaign_id: String,
    /// The campaign's slug (`InMemoryCampaign.slug` / the store's `name`) —
    /// a MACHINE key, never displayed (spec-116 FR-116-3).
    pub name: String,
    /// The derived human-facing operation codename
    /// (`campaign_menu.operation_codename`) — what the lobby DISPLAYS.
    pub codename: String,
    /// Highest tick reached.
    pub tick: u64,
    /// Lifecycle status (`"ACTIVE"` / `"ABANDONED"`).
    pub status: String,
    /// Provenance stamp: the `GameDefines` hash active when the row was
    /// written.
    pub defines_hash: String,
    /// Provenance stamp: the engine version active when the row was written.
    pub engine_version: String,
}

/// The lobby's rows and current selection.
///
/// Views never mutate app state directly: [`Self::handle_key`] returns an
/// [`AppEvent`] for the app shell to route.
pub struct LobbyView {
    /// The catalog rows, in the order the host served them.
    pub rows: Vec<LobbyRow>,
    /// The highlighted row index (saturates at `0` and `rows.len() - 1`).
    pub selected: usize,
    /// `true` when the catalog payload failed to parse — rendered as a
    /// LOUD distinct state, never conflated with a genuinely empty catalog
    /// (a serialization break must not read as a wiped database).
    pub parse_failed: bool,
}

impl LobbyView {
    /// Build a lobby view from `Host::lobby_catalog_json`'s raw JSON.
    ///
    /// Never panics: malformed JSON opens in the loud `parse_failed` state
    /// (III.11 — an unreadable catalog is an ERROR, not an empty world),
    /// while a well-formed empty array is the honest-absence state.
    #[must_use]
    pub fn from_catalog_json(raw: &str) -> Self {
        match serde_json::from_str::<Vec<LobbyRow>>(raw) {
            Ok(rows) => Self {
                rows,
                selected: 0,
                parse_failed: false,
            },
            Err(_) => Self {
                rows: Vec::new(),
                selected: 0,
                parse_failed: true,
            },
        }
    }

    /// Handle one key press, returning the routed event (if any).
    ///
    /// `Up`/`k` and `Down`/`j` move the selection, saturating at both ends
    /// (never wrapping, never panicking on an empty catalog). `Enter` loads
    /// the highlighted row's campaign (`None` when the catalog is empty).
    /// `n` mints a new campaign. `q`/`Esc` quits.
    pub fn handle_key(&mut self, code: KeyCode) -> Option<AppEvent> {
        match code {
            KeyCode::Up | KeyCode::Char('k') => {
                self.selected = self.selected.saturating_sub(1);
                None
            }
            KeyCode::Down | KeyCode::Char('j') => {
                if !self.rows.is_empty() && self.selected + 1 < self.rows.len() {
                    self.selected += 1;
                }
                None
            }
            KeyCode::Enter => self
                .rows
                .get(self.selected)
                .map(|row| AppEvent::LoadCampaign(row.campaign_id.clone())),
            KeyCode::Char('n') => Some(AppEvent::NewCampaign),
            KeyCode::Char('q') | KeyCode::Esc => Some(AppEvent::Quit),
            _ => None,
        }
    }

    /// Render the lobby into `area` of `frame`.
    ///
    /// Populated: a bordered, titled list — one line per row showing name,
    /// tick, status, engine version and defines hash (mirrors
    /// `campaign_menu.py`'s display fields), with the selected row
    /// highlighted. Empty: the honest-absence paragraph.
    pub fn render(&self, frame: &mut Frame<'_>, area: Rect) {
        let block = Block::bordered().title(LOBBY_TITLE);
        if self.parse_failed {
            let loud = Paragraph::new("Campaign catalog UNREADABLE — malformed host data.")
                .style(ratatui::style::Style::new().fg(crate::theme::CRIMSON))
                .block(block);
            frame.render_widget(loud, area);
            return;
        }
        if self.rows.is_empty() {
            frame.render_widget(Paragraph::new(EMPTY_BODY).block(block), area);
            return;
        }
        let items: Vec<ListItem<'_>> = self
            .rows
            .iter()
            .map(|row| {
                ListItem::new(format!(
                    "{}  ·  Tick {}  ·  {}  ·  engine {}  ·  defines {}",
                    row.codename, row.tick, row.status, row.engine_version, row.defines_hash
                ))
            })
            .collect();
        let list = List::new(items)
            .block(block)
            .highlight_symbol("> ")
            .highlight_style(Style::default().add_modifier(Modifier::REVERSED));
        let mut state = ListState::default();
        state.select(Some(self.selected));
        frame.render_stateful_widget(list, area, &mut state);
    }
}
