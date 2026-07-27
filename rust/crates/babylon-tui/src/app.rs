//! The client application shell (plan Task 19): view stack over the lobby
//! root, global key/mouse routing, palette + peek overlays, and headless
//! scripted-input replay.
//!
//! Views never mutate app state: their handlers return `AppEvent`s and
//! this shell routes them.
//! Every host read crosses the seam through the recording wrapper, so
//! headless transcripts can assert the exact call order (the FFI contract's
//! `host_calls`).

use std::cell::RefCell;
use std::collections::BTreeSet;
use std::io::Stdout;

use ratatui::backend::{Backend, CrosstermBackend};
use ratatui::crossterm::event::{
    self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyModifiers, MouseButton,
    MouseEvent, MouseEventKind,
};
use ratatui::crossterm::execute;
use ratatui::crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::layout::Rect;
use ratatui::Terminal;

use crate::config::{AppConfig, ScriptStep};
use crate::host::Host;
use crate::layout_registry::LayoutRegistry;
use crate::router::{parse_babylon_uri, BabylonTarget};
use crate::views::lobby::LobbyView;
use crate::views::msg::AppEvent;
use crate::views::palette::PaletteView;
use crate::views::peek::render_peek;
use crate::views::watchlist::WatchlistView;
use crate::views::wiki::WikiView;

/// One member of the view stack (the lobby is always the root).
enum View {
    /// The campaign catalog (root).
    Lobby(LobbyView),
    /// The read-only Archive dossier.
    Wiki(WikiView),
    /// The watchlist rail as a full view (M1 read-only).
    Watchlist(WatchlistView),
}

/// A [`Host`] wrapper recording every call by method name.
struct RecordingHost<'a, H: Host> {
    inner: &'a H,
    calls: &'a RefCell<Vec<String>>,
}

impl<H: Host> RecordingHost<'_, H> {
    fn record(&self, name: &str) {
        self.calls.borrow_mut().push(name.to_string());
    }
}

impl<H: Host> Host for RecordingHost<'_, H> {
    fn lobby_catalog_json(&self) -> String {
        self.record("lobby_catalog_json");
        self.inner.lobby_catalog_json()
    }

    fn load_campaign(&self, campaign_id: &str) -> String {
        self.record("load_campaign");
        self.inner.load_campaign(campaign_id)
    }

    fn read_page_json(&self, subject: &str) -> String {
        self.record("read_page_json");
        self.inner.read_page_json(subject)
    }

    fn known_subjects_json(&self) -> String {
        self.record("known_subjects_json");
        self.inner.known_subjects_json()
    }

    fn backlinks_json(&self, subject: &str) -> String {
        self.record("backlinks_json");
        self.inner.backlinks_json(subject)
    }

    fn subject_view_json(&self, subject: &str) -> String {
        self.record("subject_view_json");
        self.inner.subject_view_json(subject)
    }

    fn watchlist_json(&self) -> String {
        self.record("watchlist_json");
        self.inner.watchlist_json()
    }

    fn pacing_state_json(&self) -> String {
        self.record("pacing_state_json");
        self.inner.pacing_state_json()
    }

    fn advance_tick(&self) -> String {
        self.record("advance_tick");
        self.inner.advance_tick()
    }

    fn run_until_paused(&self) -> String {
        self.record("run_until_paused");
        self.inner.run_until_paused()
    }

    fn acknowledge_pause(&self) -> String {
        self.record("acknowledge_pause");
        self.inner.acknowledge_pause()
    }

    fn chronicle_rail_json(&self) -> String {
        self.record("chronicle_rail_json");
        self.inner.chronicle_rail_json()
    }

    fn verb_plate_view_json(&self) -> String {
        self.record("verb_plate_view_json");
        self.inner.verb_plate_view_json()
    }

    fn issue_verb(&self, args_json: &str) -> String {
        self.record("issue_verb");
        self.inner.issue_verb(args_json)
    }

    fn endgame_status_json(&self) -> String {
        self.record("endgame_status_json");
        self.inner.endgame_status_json()
    }

    fn pin_watchlist(&self, args_json: &str) -> String {
        self.record("pin_watchlist");
        self.inner.pin_watchlist(args_json)
    }

    fn nav_state_json(&self) -> String {
        self.record("nav_state_json");
        self.inner.nav_state_json()
    }

    fn save_nav_state(&self, nav_json: &str) -> String {
        self.record("save_nav_state");
        self.inner.save_nav_state(nav_json)
    }
}

/// The client application: config + host seam + the M1 view stack.
pub struct App<H: Host> {
    cfg: AppConfig,
    host: H,
    calls: RefCell<Vec<String>>,
    views: Vec<View>,
    /// The command palette overlay; `Some` while open (keys route to it
    /// first, mirroring the Textual client's modal palette).
    palette: Option<PaletteView>,
    /// Per-frame widget→rect→entity map for mouse hit-testing.
    registry: LayoutRegistry,
    /// Known page subjects, fetched once on first Archive entry.
    known: Option<BTreeSet<String>>,
    /// The entity under the mouse cursor (hover), if any.
    peek_target: Option<String>,
    /// Peek overlay depth, 0 = off (K cycles 0→1→2→3→0).
    peek_depth: u8,
    /// Cache of the last peek fetch: `(subject, view json)` — the seam is
    /// crossed once per subject, not once per frame (M1 views are frozen
    /// per campaign bind; M2 tick advances invalidate by subject change).
    peek_cache: Option<(String, String)>,
}

impl<H: Host> App<H> {
    /// Build the app over a parsed config and a host implementation; the
    /// lobby view is the root of the stack from the first frame.
    pub fn new(cfg: AppConfig, host: H) -> Self {
        Self {
            cfg,
            host,
            calls: RefCell::new(Vec::new()),
            views: Vec::new(),
            palette: None,
            registry: LayoutRegistry::new(),
            known: None,
            peek_target: None,
            peek_depth: 0,
            peek_cache: None,
        }
    }

    /// Host-method names invoked so far, in call order.
    pub fn host_calls(&self) -> Vec<String> {
        self.calls.borrow().clone()
    }

    fn recording(&self) -> RecordingHost<'_, H> {
        RecordingHost {
            inner: &self.host,
            calls: &self.calls,
        }
    }

    /// Lazily fetch + cache the known-subjects set (first Archive entry).
    fn ensure_known(&mut self) {
        if self.known.is_none() {
            let raw = self.recording().known_subjects_json();
            let subjects: Vec<String> = serde_json::from_str(&raw).unwrap_or_default();
            self.known = Some(subjects.into_iter().collect());
        }
    }

    /// Lazily build the root lobby view on first render.
    fn ensure_root(&mut self) {
        if self.views.is_empty() {
            let raw = self.recording().lobby_catalog_json();
            self.views
                .push(View::Lobby(LobbyView::from_catalog_json(&raw)));
        }
    }

    /// Render one frame into `terminal`.
    ///
    /// ratatui 0.30 gives `Backend` an associated `Error` type, so this
    /// returns `Result<(), B::Error>` (the plan's `io::Result` was the
    /// 0.29-era shape of the same contract).
    pub fn render_frame<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> Result<(), B::Error> {
        self.ensure_root();
        // Pre-fetch overlay data outside the draw closure (single writer:
        // the host is never called mid-draw).
        let peek_json = match (&self.peek_target, self.peek_depth) {
            (Some(subject), depth) if depth > 0 => {
                let cached = self
                    .peek_cache
                    .as_ref()
                    .filter(|(cached_subject, _)| cached_subject == subject)
                    .map(|(_, json)| json.clone());
                Some(match cached {
                    Some(json) => json,
                    None => {
                        let json = self.recording().subject_view_json(subject);
                        self.peek_cache = Some((subject.clone(), json.clone()));
                        json
                    }
                })
            }
            _ => None,
        };
        let title = format!("The Archive — {}", self.cfg.campaign_name);
        let known = self.known.clone().unwrap_or_default();
        let views = &mut self.views;
        let registry = &mut self.registry;
        let palette = &self.palette;
        let peek_depth = self.peek_depth;
        terminal.draw(|frame| {
            registry.clear();
            let area = frame.area();
            match views.last_mut() {
                Some(View::Lobby(lobby)) => lobby.render(frame, area),
                Some(View::Wiki(wiki)) => wiki.render(frame, area, registry, &known),
                Some(View::Watchlist(watchlist)) => watchlist.render(frame, area),
                None => unreachable!("ensure_root always seeds the lobby"),
            }
            if let Some(palette) = palette {
                palette.render(frame, area);
            }
            if let Some(json) = &peek_json {
                let overlay = peek_overlay_area(area);
                // Clear first: widgets only write where they have content,
                // so the view underneath would bleed through unwritten cells.
                frame.render_widget(ratatui::widgets::Clear, overlay);
                render_peek(frame, overlay, json, peek_depth);
            }
            let _ = title; // chrome title is owned by each view's block (M1)
        })?;
        Ok(())
    }

    /// Handle one key event. Returns `true` when the app should quit.
    pub fn handle_key(&mut self, code: KeyCode, modifiers: KeyModifiers) -> bool {
        // Palette is modal: it sees every key while open.
        if let Some(palette) = &mut self.palette {
            if let Some(ev) = palette.handle_key(code) {
                if matches!(ev, AppEvent::Back) {
                    self.palette = None;
                    return false;
                }
                self.palette = None;
                return self.route(ev);
            }
            return false;
        }
        // Global bindings (Task 19): palette, peek, view-switch scaffold.
        match code {
            KeyCode::Char('/') => {
                // One seam crossing refreshes BOTH consumers: the palette
                // and the redlink-styling cache (which would otherwise stay
                // frozen at first campaign entry while ticks bake pages).
                let raw = self.recording().known_subjects_json();
                let subjects: Vec<String> = serde_json::from_str(&raw).unwrap_or_default();
                self.known = Some(subjects.into_iter().collect());
                self.palette = Some(PaletteView::open(&raw));
                return false;
            }
            KeyCode::Char('K') => {
                self.peek_depth = (self.peek_depth + 1) % 4;
                return false;
            }
            KeyCode::Tab => {
                self.toggle_watchlist();
                return false;
            }
            // '1'–'5' view switch scaffold: only the wiki ('3', mirroring
            // the Textual shell's dashboard/map/wiki/topology order) is
            // routable in M1; the rest are reserved no-ops until their
            // views exist (M4+).
            KeyCode::Char('3') if self.in_campaign() => {
                self.focus_wiki();
                return false;
            }
            _ => {}
        }
        let ev = match self.views.last_mut() {
            Some(View::Lobby(lobby)) => lobby.handle_key(code),
            Some(View::Wiki(wiki)) => wiki.handle_key(code, modifiers),
            Some(View::Watchlist(watchlist)) => watchlist.handle_key(code),
            None => None,
        };
        // Keyboard peek is first-class (S7 canon): the wiki link cursor
        // feeds the peek target exactly like mouse hover does.
        if let Some(View::Wiki(wiki)) = self.views.last() {
            if let Some(target) = wiki.focused_target() {
                self.peek_target = Some(target.to_string());
            }
        }
        match ev {
            Some(ev) => self.route(ev),
            None => false,
        }
    }

    /// Handle one mouse event: hover feeds the peek target, left-click
    /// navigates the hit entity. Never quits.
    pub fn handle_mouse(&mut self, ev: MouseEvent) -> bool {
        match ev.kind {
            MouseEventKind::Moved => {
                self.peek_target = self
                    .registry
                    .hit(ev.column, ev.row)
                    .and_then(|(_, _, entity)| entity.clone());
            }
            MouseEventKind::Down(MouseButton::Left) => {
                let target = self
                    .registry
                    .hit(ev.column, ev.row)
                    .and_then(|(_, _, entity)| entity.clone());
                if let Some(subject) = target {
                    return self.route(AppEvent::OpenSubject(subject));
                }
            }
            _ => {}
        }
        false
    }

    /// Apply one headless script step. Returns `true` on quit.
    pub fn apply_step(&mut self, step: &ScriptStep) -> bool {
        match step {
            ScriptStep::Key { key } => match key_event_from_name(key) {
                Some((code, modifiers)) => self.handle_key(code, modifiers),
                None => false, // unknown key names are transcript-visible no-ops
            },
            ScriptStep::Mouse { mouse: (col, row) } => self.handle_mouse(MouseEvent {
                kind: MouseEventKind::Down(MouseButton::Left),
                column: *col,
                row: *row,
                modifiers: KeyModifiers::NONE,
            }),
        }
    }

    /// Route a view-emitted [`AppEvent`]. Returns `true` on quit.
    fn route(&mut self, ev: AppEvent) -> bool {
        match ev {
            AppEvent::LoadCampaign(campaign_id) => {
                // Bind the session Python-side FIRST (the composition-root
                // verb the M1 verify panel found missing), THEN read pages.
                let ack = self.recording().load_campaign(&campaign_id);
                let ok = serde_json::from_str::<serde_json::Value>(&ack)
                    .ok()
                    .and_then(|v| v.get("ok").and_then(serde_json::Value::as_bool))
                    .unwrap_or(false);
                self.peek_target = None;
                if !ok {
                    // Loud failure page — an error is never an empty world
                    // (Constitution III.11); the ack carries the real error.
                    let error = serde_json::from_str::<serde_json::Value>(&ack)
                        .ok()
                        .and_then(|v| {
                            v.get("error")
                                .and_then(serde_json::Value::as_str)
                                .map(str::to_string)
                        })
                        .unwrap_or_else(|| ack.clone());
                    let markdown =
                        format!("# Campaign load failed\n\nCampaign `{campaign_id}`:\n\n{error}");
                    self.push_failure_page("load-failure", &markdown);
                    return false;
                }
                // Known subjects only exist once a session is bound —
                // (re)fetch AFTER the bind, never before.
                self.known = None;
                self.ensure_known();
                // Textual parity: the first page after campaign selection is
                // the briefing subject (honest absence when unbaked).
                let subject = format!("briefing/{campaign_id}");
                self.open_in_wiki(&BabylonTarget::Entity(subject));
                false
            }
            // M1 is read-only: the new-campaign write path lands in M2
            // (plan Task 25 wires writes); until then the intent is a no-op.
            AppEvent::NewCampaign => false,
            AppEvent::OpenSubject(subject) => {
                self.peek_target = None;
                self.ensure_known();
                let target = if subject.starts_with("babylon://") {
                    parse_babylon_uri(&subject).unwrap_or(BabylonTarget::Redlink(subject))
                } else {
                    BabylonTarget::Entity(subject)
                };
                self.open_in_wiki(&target);
                false
            }
            AppEvent::Back => {
                self.peek_target = None;
                if self.views.len() > 1 {
                    self.views.pop();
                    false
                } else {
                    true // q at the lobby root quits, like M0
                }
            }
            AppEvent::Quit => true,
        }
    }

    /// Push (or reuse) a wiki view showing the loud campaign-load-failure
    /// page — an error is never rendered as an empty world.
    fn push_failure_page(&mut self, campaign_id: &str, error: &str) {
        let markdown = format!("# Campaign load failed\n\nCampaign `{campaign_id}`:\n\n{error}");
        if let Some(View::Wiki(wiki)) = self.views.last_mut() {
            wiki.open_page("load-failure", markdown);
            return;
        }
        let mut wiki = WikiView::new();
        wiki.open_page("load-failure", markdown);
        self.views.push(View::Wiki(wiki));
    }

    /// Open `target` in the topmost wiki view, unwinding any views stacked
    /// above it first (Enter-from-watchlist must reuse the wiki and its
    /// jumplist, never grow the stack without bound); pushes a fresh wiki
    /// only when none exists on the stack at all.
    fn open_in_wiki(&mut self, target: &BabylonTarget) {
        if self.views.iter().any(|v| matches!(v, View::Wiki(_))) {
            while !matches!(self.views.last(), Some(View::Wiki(_))) {
                self.views.pop();
            }
        }
        let recording = RecordingHost {
            inner: &self.host,
            calls: &self.calls,
        };
        if let Some(View::Wiki(wiki)) = self.views.last_mut() {
            wiki.open(target, &recording);
            return;
        }
        let mut wiki = WikiView::new();
        wiki.open(target, &recording);
        self.views.push(View::Wiki(wiki));
    }

    /// Whether a campaign view (wiki/watchlist) is anywhere on the stack.
    fn in_campaign(&self) -> bool {
        self.views
            .iter()
            .any(|v| matches!(v, View::Wiki(_) | View::Watchlist(_)))
    }

    /// Tab: toggle between the wiki and the watchlist view (campaign only).
    fn toggle_watchlist(&mut self) {
        match self.views.last() {
            Some(View::Wiki(_)) => {
                let raw = self.recording().watchlist_json();
                self.views.push(View::Watchlist(WatchlistView::open(&raw)));
            }
            Some(View::Watchlist(_)) => {
                self.views.pop();
            }
            _ => {}
        }
    }

    /// Pop back to the topmost wiki view if one exists below the top.
    fn focus_wiki(&mut self) {
        while matches!(self.views.last(), Some(View::Watchlist(_))) {
            self.views.pop();
        }
    }
}

/// The centered rect the peek overlay renders into (bottom-right quadrant,
/// mirroring the Textual peek panel's placement).
fn peek_overlay_area(area: Rect) -> Rect {
    let w = area.width / 2;
    let h = area.height / 2;
    Rect::new(area.x + area.width - w, area.y + area.height - h, w, h)
}

/// Map a script key name to a crossterm key event (plan Task 19 headless
/// replay). `None` for unknown names — a loud transcript no-op, never a
/// guessed key.
pub fn key_event_from_name(name: &str) -> Option<(KeyCode, KeyModifiers)> {
    if let Some(rest) = name.strip_prefix("ctrl-") {
        let mut chars = rest.chars();
        let (Some(c), None) = (chars.next(), chars.next()) else {
            return None;
        };
        return Some((KeyCode::Char(c), KeyModifiers::CONTROL));
    }
    let code = match name {
        "enter" => KeyCode::Enter,
        "esc" => KeyCode::Esc,
        "up" => KeyCode::Up,
        "down" => KeyCode::Down,
        "left" => KeyCode::Left,
        "right" => KeyCode::Right,
        "tab" => KeyCode::Tab,
        "backspace" => KeyCode::Backspace,
        "pageup" => KeyCode::PageUp,
        "pagedown" => KeyCode::PageDown,
        _ => {
            let mut chars = name.chars();
            let (Some(c), None) = (chars.next(), chars.next()) else {
                return None;
            };
            KeyCode::Char(c)
        }
    };
    Some((code, KeyModifiers::NONE))
}

/// RAII terminal session: raw mode + alternate screen + mouse capture on
/// construction, restored on Drop — INCLUDING the unwind path (a panicking
/// host callback must never leave the user's terminal raw; the restore
/// runs before the panic re-crosses the FFI as a Python exception).
struct TerminalSession;

impl TerminalSession {
    fn enter() -> std::io::Result<Self> {
        enable_raw_mode()?;
        execute!(std::io::stdout(), EnterAlternateScreen, EnableMouseCapture)?;
        Ok(Self)
    }
}

impl Drop for TerminalSession {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let _ = execute!(std::io::stdout(), LeaveAlternateScreen, DisableMouseCapture);
    }
}

/// Run the interactive client: crossterm init (alternate screen + mouse
/// capture) → render/input loop → restore (via the RAII session guard's Drop,
/// on success, error, AND panic paths alike). Returns the recorded
/// host-call names.
///
/// Always uses the `ratatui::crossterm` re-export, never a direct crossterm
/// dependency (version-skew constraint from the plan).
pub fn run_interactive<H: Host>(mut app: App<H>) -> std::io::Result<Vec<String>> {
    let _session = TerminalSession::enter()?;
    let backend: CrosstermBackend<Stdout> = CrosstermBackend::new(std::io::stdout());
    let mut terminal = Terminal::new(backend)?;
    loop {
        app.render_frame(&mut terminal)?;
        match event::read()? {
            Event::Key(key) => {
                if app.handle_key(key.code, key.modifiers) {
                    break;
                }
            }
            Event::Mouse(mouse) => {
                if app.handle_mouse(mouse) {
                    break;
                }
            }
            _ => {} // resize redraws on the next loop pass
        }
    }
    Ok(app.host_calls())
}
