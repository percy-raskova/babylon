//! The client application shell: M0 renders the lobby hello-frame.

use ratatui::backend::Backend;
use ratatui::widgets::{Block, List, Paragraph};
use ratatui::Terminal;
use serde::Deserialize;

use crate::config::AppConfig;
use crate::host::Host;

/// One lobby catalog row as served by `Host::lobby_catalog_json` (design §4).
#[derive(Debug, Deserialize)]
struct LobbyRow {
    campaign_id: String,
    name: String,
    tick: u64,
}

/// The client application: config + host seam, renders frames.
pub struct App<H: Host> {
    cfg: AppConfig,
    host: H,
}

impl<H: Host> App<H> {
    /// Build the app over a parsed config and a host implementation.
    pub fn new(cfg: AppConfig, host: H) -> Self {
        Self { cfg, host }
    }

    /// Render one frame into `terminal` (M0: the lobby hello-frame).
    ///
    /// ratatui 0.30 gives `Backend` an associated `Error` type, so this
    /// returns `Result<(), B::Error>` (the plan's `io::Result` was the
    /// 0.29-era shape of the same contract).
    pub fn render_frame<B: Backend>(&self, terminal: &mut Terminal<B>) -> Result<(), B::Error> {
        let raw = self.host.lobby_catalog_json();
        let rows: Vec<LobbyRow> = serde_json::from_str(&raw).unwrap_or_default();
        let title = format!("The Archive — {}", self.cfg.campaign_name);
        terminal.draw(|frame| {
            let block = Block::bordered().title(title.as_str());
            if rows.is_empty() {
                // Honest absence (III.11): an empty catalog is a loud state,
                // never a fabricated placeholder row.
                let empty = Paragraph::new("No campaigns in the catalog.").block(block);
                frame.render_widget(empty, frame.area());
            } else {
                let items: Vec<String> = rows
                    .iter()
                    .map(|r| format!("{}  [{}] tick {}", r.name, r.campaign_id, r.tick))
                    .collect();
                let list = List::new(items).block(block);
                frame.render_widget(list, frame.area());
            }
        })?;
        Ok(())
    }
}
