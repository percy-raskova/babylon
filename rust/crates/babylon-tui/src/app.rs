//! The client application shell: M0 renders the lobby hello-frame.

use std::cell::RefCell;
use std::io::Stdout;

use ratatui::backend::{Backend, CrosstermBackend};
use ratatui::crossterm::event::{self, Event, KeyCode};
use ratatui::crossterm::execute;
use ratatui::crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
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
///
/// Every host read is recorded by method name so headless transcripts can
/// assert the seam was exercised (the FFI contract's `host_calls`).
pub struct App<H: Host> {
    cfg: AppConfig,
    host: H,
    calls: RefCell<Vec<String>>,
}

impl<H: Host> App<H> {
    /// Build the app over a parsed config and a host implementation.
    pub fn new(cfg: AppConfig, host: H) -> Self {
        Self {
            cfg,
            host,
            calls: RefCell::new(Vec::new()),
        }
    }

    /// Host-method names invoked so far, in call order.
    pub fn host_calls(&self) -> Vec<String> {
        self.calls.borrow().clone()
    }

    /// Render one frame into `terminal` (M0: the lobby hello-frame).
    ///
    /// ratatui 0.30 gives `Backend` an associated `Error` type, so this
    /// returns `Result<(), B::Error>` (the plan's `io::Result` was the
    /// 0.29-era shape of the same contract).
    pub fn render_frame<B: Backend>(&self, terminal: &mut Terminal<B>) -> Result<(), B::Error> {
        self.calls.borrow_mut().push("lobby_catalog_json".into());
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

/// Run the interactive M0 client: crossterm init → hello-frame → quit on
/// `q`/`Esc` → restore. Returns the recorded host-call names.
///
/// Always uses the `ratatui::crossterm` re-export, never a direct crossterm
/// dependency (version-skew constraint from the plan).
pub fn run_interactive<H: Host>(app: App<H>) -> std::io::Result<Vec<String>> {
    enable_raw_mode()?;
    let mut stdout = std::io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend: CrosstermBackend<Stdout> = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;
    let mut run = || -> std::io::Result<()> {
        app.render_frame(&mut terminal)?;
        loop {
            if let Event::Key(key) = event::read()? {
                if matches!(key.code, KeyCode::Char('q') | KeyCode::Esc) {
                    return Ok(());
                }
            }
        }
    };
    let result = run();
    disable_raw_mode()?;
    execute!(std::io::stdout(), LeaveAlternateScreen)?;
    result.map(|()| app.host_calls())
}
