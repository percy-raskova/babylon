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
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::Terminal;
use serde::Deserialize;

use crate::config::{AppConfig, ScriptStep};
use crate::host::Host;
use crate::layout_registry::LayoutRegistry;
use crate::router::{parse_babylon_uri, BabylonTarget};
use crate::views::chronicle::ChronicleRail;
use crate::views::hud::HudStrip;
use crate::views::lobby::LobbyView;
use crate::views::msg::AppEvent;
use crate::views::palette::PaletteView;
use crate::views::peek::render_peek;
use crate::views::verbs::VerbPlateView;
use crate::views::watchlist::WatchlistView;
use crate::views::wiki::WikiView;

/// One member of the view stack (the lobby is always the root).
///
/// M2 dissolved the M1 full-screen watchlist view: the watchlist is now the
/// play chrome's persistent LEFT rail (design §7), not a stack member.
enum View {
    /// The campaign catalog (root).
    Lobby(LobbyView),
    /// The Archive dossier (the play screen's center pane once bound).
    Wiki(WikiView),
}

/// Which play-chrome pane keyboard focus is on (`Tab` cycles).
///
/// The verb plate and HUD are passive chrome (F-keys and `t`/`r`/`a` are
/// global) — only the three navigable panes take focus.
#[derive(Clone, Copy, PartialEq, Eq)]
enum ChromeFocus {
    /// The wiki dossier (center pane).
    Center,
    /// The chronicle rail (right).
    Chronicle,
    /// The watchlist rail (left).
    Watchlist,
}

/// The paced-driver state pre-checked before every tick verb (contract §1;
/// the Textual client's locked → awaiting_ack → busy refusal order).
#[derive(Debug, Deserialize)]
struct PacingSnapshot {
    attached: bool,
    locked: bool,
    lock_reason: Option<String>,
    awaiting_ack: bool,
    pause_summary: Option<String>,
    busy: bool,
    /// Never on the wire — set only by [`Self::unreadable`] so the refusal
    /// ladder can name the parse failure AS a parse failure instead of
    /// fabricating a "campaign ended" claim (verify-panel finding: a
    /// confidently-wrong terminal-state readout violates III.11 as much as
    /// a silent default does).
    #[serde(default)]
    unreadable: bool,
}

impl PacingSnapshot {
    /// A parse failure is a LOUD first-class refusal, never a fabricated
    /// locked/ready state.
    fn unreadable() -> Self {
        Self {
            attached: true,
            locked: false,
            lock_reason: None,
            awaiting_ack: false,
            pause_summary: None,
            busy: false,
            unreadable: true,
        }
    }
}

/// The persistent play-screen chrome, created when a campaign binds and
/// dropped on return to the lobby (design §7: HUD top, watchlist rail LEFT,
/// wiki center, chronicle rail RIGHT, verb plate BOTTOM, status line).
struct PlayChrome {
    hud: HudStrip,
    chronicle: ChronicleRail,
    verbs: VerbPlateView,
    watchlist: WatchlistView,
    focus: ChromeFocus,
}

impl PlayChrome {
    fn new() -> Self {
        Self {
            hud: HudStrip::new(),
            chronicle: ChronicleRail::default(),
            verbs: VerbPlateView::open("null"),
            watchlist: WatchlistView::open("[]"),
            focus: ChromeFocus::Center,
        }
    }
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
    /// The play-screen chrome; `Some` while a campaign is bound.
    chrome: Option<PlayChrome>,
    /// The one-line status readout (refusals, tick acks, verb queue acks) —
    /// the Textual `#status` label's single shared line, verbatim strings.
    status: Option<String>,
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
            chrome: None,
            status: None,
        }
    }

    /// Host-method names invoked so far, in call order.
    pub fn host_calls(&self) -> Vec<String> {
        self.calls.borrow().clone()
    }

    /// The wrapped host (integration tests inspect their stateful fakes
    /// through this; production callers never need it).
    pub fn host_ref(&self) -> &H {
        &self.host
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
        let chrome = &mut self.chrome;
        let status = self.status.clone();
        terminal.draw(|frame| {
            registry.clear();
            let area = frame.area();
            match (views.last_mut(), chrome.as_mut()) {
                // The play screen (design §7): HUD top, watchlist rail LEFT,
                // wiki center, chronicle rail RIGHT, verb plate BOTTOM, one
                // status line.
                (Some(View::Wiki(wiki)), Some(chrome)) => {
                    let [hud_area, mid_area, plate_area, status_area] = Layout::vertical([
                        Constraint::Length(3),
                        Constraint::Min(5),
                        Constraint::Length(8),
                        Constraint::Length(1),
                    ])
                    .areas(area);
                    let [watch_area, center_area, chron_area] = Layout::horizontal([
                        Constraint::Length(24),
                        Constraint::Min(20),
                        Constraint::Length(24),
                    ])
                    .areas(mid_area);
                    chrome.hud.render(frame, hud_area);
                    chrome.watchlist.render(
                        frame,
                        watch_area,
                        chrome.focus == ChromeFocus::Watchlist,
                    );
                    wiki.render(frame, center_area, registry, &known);
                    chrome.chronicle.render(
                        frame,
                        chron_area,
                        chrome.focus == ChromeFocus::Chronicle,
                    );
                    chrome.verbs.render(frame, plate_area, registry);
                    if let Some(text) = &status {
                        frame.render_widget(ratatui::text::Line::from(text.as_str()), status_area);
                    }
                }
                (Some(View::Lobby(lobby)), _) => {
                    if let Some(text) = &status {
                        let [lobby_area, status_area] =
                            Layout::vertical([Constraint::Min(3), Constraint::Length(1)])
                                .areas(area);
                        lobby.render(frame, lobby_area);
                        frame.render_widget(ratatui::text::Line::from(text.as_str()), status_area);
                    } else {
                        lobby.render(frame, area);
                    }
                }
                (Some(View::Wiki(wiki)), None) => wiki.render(frame, area, registry, &known),
                (None, _) => unreachable!("ensure_root always seeds the lobby"),
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
            KeyCode::Tab if self.chrome.is_some() => {
                // Focus cycles the three navigable panes; passive chrome
                // (HUD, verb plate) never takes focus.
                if let Some(chrome) = self.chrome.as_mut() {
                    chrome.focus = match chrome.focus {
                        ChromeFocus::Center => ChromeFocus::Chronicle,
                        ChromeFocus::Chronicle => ChromeFocus::Watchlist,
                        ChromeFocus::Watchlist => ChromeFocus::Center,
                    };
                }
                return false;
            }
            // '1'–'5' view switch scaffold: only the wiki ('3', mirroring
            // the Textual shell's dashboard/map/wiki/topology order) is
            // routable; the rest are reserved no-ops until their views
            // exist (M4+). With chrome, '3' returns focus to the center.
            KeyCode::Char('3') if self.in_campaign() => {
                if let Some(chrome) = self.chrome.as_mut() {
                    chrome.focus = ChromeFocus::Center;
                }
                return false;
            }
            // Tick controls (contract §1) — global while a campaign is
            // bound, exactly like the Textual t/r/a bindings.
            KeyCode::Char('t') if self.chrome.is_some() => {
                self.cmd_advance_tick();
                return false;
            }
            KeyCode::Char('r') if self.chrome.is_some() => {
                self.cmd_run_until_paused();
                return false;
            }
            KeyCode::Char('a') if self.chrome.is_some() => {
                self.cmd_acknowledge_pause();
                return false;
            }
            // 'P' pins the CURRENT dossier subject (contract §6: lowercase
            // 'p' stays the wiki link-cursor — the recorded divergence from
            // Textual's 'p'=pin).
            KeyCode::Char('P') if self.chrome.is_some() => {
                self.cmd_toggle_pin(None);
                return false;
            }
            KeyCode::F(n @ 1..=9) if self.chrome.is_some() => {
                self.cmd_issue_verb(usize::from(n) - 1);
                return false;
            }
            _ => {}
        }
        // Focused-rail routing: while a rail holds focus its cursor keys
        // never reach the wiki view underneath. The rail borrow is dropped
        // before any command/route call re-borrows `self`.
        enum RailAction {
            Fall,
            Handled,
            Route(AppEvent),
            Pin(Option<String>),
        }
        let rail_action = match self.chrome.as_mut() {
            Some(chrome)
                if chrome.focus == ChromeFocus::Chronicle
                    && matches!(code, KeyCode::Up | KeyCode::Down | KeyCode::Enter) =>
            {
                match chrome.chronicle.handle_key(code) {
                    Some(ev) => {
                        chrome.focus = ChromeFocus::Center;
                        RailAction::Route(ev)
                    }
                    None => RailAction::Handled,
                }
            }
            Some(chrome)
                if chrome.focus == ChromeFocus::Watchlist
                    && matches!(code, KeyCode::Up | KeyCode::Down | KeyCode::Enter) =>
            {
                match chrome.watchlist.handle_key(code) {
                    Some(ev) => {
                        chrome.focus = ChromeFocus::Center;
                        RailAction::Route(ev)
                    }
                    None => RailAction::Handled,
                }
            }
            // In the watchlist rail 'p' toggles the highlighted row's pin
            // (no link cursor exists here — contract §6).
            Some(chrome)
                if chrome.focus == ChromeFocus::Watchlist && code == KeyCode::Char('p') =>
            {
                let subject = chrome
                    .watchlist
                    .rows
                    .get(chrome.watchlist.selected)
                    .and_then(|row| row.get("subject"))
                    .and_then(serde_json::Value::as_str)
                    .map(str::to_string);
                RailAction::Pin(subject)
            }
            _ => RailAction::Fall,
        };
        match rail_action {
            RailAction::Handled => return false,
            RailAction::Route(ev) => return self.route(ev),
            RailAction::Pin(subject) => {
                self.cmd_toggle_pin(subject);
                return false;
            }
            RailAction::Fall => {}
        }
        let ev = match self.views.last_mut() {
            Some(View::Lobby(lobby)) => lobby.handle_key(code),
            Some(View::Wiki(wiki)) => wiki.handle_key(code, modifiers),
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
                    .and_then(|(_, _, entity)| entity.clone())
                    // Verb rows are dispatch zones, not peekable entities.
                    .filter(|entity| !entity.starts_with("verb:"));
            }
            MouseEventKind::Down(MouseButton::Left) => {
                let target = self
                    .registry
                    .hit(ev.column, ev.row)
                    .and_then(|(_, _, entity)| entity.clone());
                if let Some(subject) = target {
                    // A click on a verb row dispatches exactly like its
                    // F-key (plan Task 23's "F1–F9 + click dispatch").
                    if let Some(slot) = subject
                        .strip_prefix("verb:")
                        .and_then(|raw| raw.parse::<usize>().ok())
                    {
                        self.cmd_issue_verb(slot);
                        return false;
                    }
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
                // A different campaign's stat plates must never serve from
                // the previous bind's cache (verify-panel finding).
                self.peek_cache = None;
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
                // Nav restore rides a post-bind pull (contract §5 — never
                // config_json, which predates selection).
                let nav_raw = self.recording().nav_state_json();
                let restored: Vec<String> = serde_json::from_str::<serde_json::Value>(&nav_raw)
                    .ok()
                    .and_then(|v| {
                        v.get("jumplist")
                            .and_then(|j| serde_json::from_value(j.clone()).ok())
                    })
                    .unwrap_or_default();
                // Textual parity: the first page after campaign selection is
                // the briefing subject (honest absence when unbaked).
                let subject = format!("briefing/{campaign_id}");
                self.open_in_wiki(&BabylonTarget::Entity(subject));
                if !restored.is_empty() {
                    if let Some(View::Wiki(wiki)) = self.views.last_mut() {
                        // Seed the restored history BELOW the briefing visit
                        // (the briefing stays current, `[` walks into the
                        // restored trail). A trailing restored entry equal
                        // to the fresh briefing visit is dropped first —
                        // without the dedupe every resume appends another
                        // briefing entry and the persisted jumplist grows
                        // without bound (verify-panel finding).
                        let mut entries = restored;
                        if entries.last() == wiki.jumplist.first() {
                            entries.pop();
                        }
                        entries.append(&mut wiki.jumplist);
                        wiki.jumplist = entries;
                        wiki.jumplist_idx = wiki.jumplist.len().saturating_sub(1);
                    }
                }
                // The bind ack carries the session's current tick (a resumed
                // campaign is NOT at tick 0 — honesty over a zeroed counter).
                let tick = serde_json::from_str::<serde_json::Value>(&ack)
                    .ok()
                    .and_then(|v| v.get("tick").and_then(serde_json::Value::as_u64))
                    .unwrap_or(0);
                let mut chrome = PlayChrome::new();
                chrome.hud.set_tick(tick);
                self.chrome = Some(chrome);
                self.refresh_chrome();
                false
            }
            // Campaign MINTING never made M2's write set (Task 25 is
            // watchlist/nav): refuse loudly rather than no-op silently —
            // minting stays on the Textual lobby until its own task lands.
            AppEvent::NewCampaign => {
                self.status = Some(
                    "status: new-campaign minting is not wired in this client yet — \
                     use the Textual lobby (babylon play)"
                        .to_string(),
                );
                false
            }
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
                    // Leaving the campaign (the pop returns to the lobby
                    // root): persist nav BEFORE the pop drops the wiki view
                    // whose jumplist is the payload, then drop the chrome
                    // (contract §5 cadence).
                    let leaving_campaign = matches!(self.views.last(), Some(View::Wiki(_)))
                        && self
                            .views
                            .iter()
                            .filter(|v| matches!(v, View::Wiki(_)))
                            .count()
                            == 1;
                    if leaving_campaign {
                        self.save_nav();
                    }
                    self.views.pop();
                    if leaving_campaign {
                        self.chrome = None;
                        self.status = None;
                    }
                    false
                } else {
                    true // q at the lobby root quits, like M0 (nav already
                         // saved when the campaign was left — the chrome is
                         // always gone by the time the lobby is on top, so a
                         // save call here could never fire; recorded in
                         // contract §5: Back-to-lobby is the sole save point)
                }
            }
            AppEvent::Quit => true,
        }
    }

    /// Persist the wiki jumplist via `save_nav_state` (contract §5) — on
    /// quit and on leaving the campaign. Breadcrumbs persist empty: this
    /// client tracks no breadcrumb trail yet (an honest absence, not a
    /// stub — the Textual client never persisted nav in production at all).
    fn save_nav(&mut self) {
        if self.chrome.is_none() {
            return;
        }
        let entries: Vec<String> = self
            .views
            .iter()
            .find_map(|v| match v {
                View::Wiki(wiki) => Some(wiki.jumplist.clone()),
                View::Lobby(_) => None,
            })
            .unwrap_or_default();
        if entries.is_empty() {
            return;
        }
        let payload = serde_json::json!({"jumplist": entries, "breadcrumbs": []}).to_string();
        let _ack = self.recording().save_nav_state(&payload);
        // The ack is transcript-recorded; on the quit path there is no
        // frame left to render a refusal into, and a system-level failure
        // panics loudly inside the host itself (III.11).
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

    /// Whether a campaign view is anywhere on the stack.
    fn in_campaign(&self) -> bool {
        self.views.iter().any(|v| matches!(v, View::Wiki(_)))
    }

    /// Pull + parse the paced-driver state (contract §1). A malformed
    /// payload is a LOUD pretend-locked snapshot, never a ready default.
    fn pacing_snapshot(&mut self) -> PacingSnapshot {
        let raw = self.recording().pacing_state_json();
        if let Some(chrome) = self.chrome.as_mut() {
            // One pull feeds BOTH consumers: the refusal ladder and the
            // HUD's PACING line, which must never contradict each other.
            chrome.hud.update_pacing(&raw);
        }
        serde_json::from_str(&raw).unwrap_or_else(|_| PacingSnapshot::unreadable())
    }

    /// The Textual pre-check ladder (locked → awaiting_ack → busy,
    /// `app.py:2219-2242`): `Some(refusal)` when a tick verb must not fire.
    fn tick_refusal(snapshot: &PacingSnapshot) -> Option<String> {
        if snapshot.unreadable {
            return Some(
                "pacing state UNREADABLE — malformed host data; refusing to tick".to_string(),
            );
        }
        if !snapshot.attached {
            return Some("no campaign attached".to_string());
        }
        if snapshot.locked {
            let reason = snapshot.lock_reason.as_deref().unwrap_or("unknown");
            return Some(format!("campaign ended — {reason}"));
        }
        if snapshot.awaiting_ack {
            let summary = snapshot.pause_summary.as_deref().unwrap_or("autopause");
            return Some(format!(
                "autopause pending ({summary}) — press 'a' to acknowledge"
            ));
        }
        if snapshot.busy {
            return Some("a run is already in progress — please wait".to_string());
        }
        None
    }

    /// `t` — advance exactly one tick (contract §1).
    fn cmd_advance_tick(&mut self) {
        let snapshot = self.pacing_snapshot();
        if let Some(refusal) = Self::tick_refusal(&snapshot) {
            self.status = Some(format!("status: {refusal}"));
            return;
        }
        let raw = self.recording().advance_tick();
        let value: serde_json::Value = match serde_json::from_str(&raw) {
            Ok(value) => value,
            Err(_) => {
                self.status = Some("status: advance_tick UNREADABLE — malformed host data".into());
                return;
            }
        };
        if value.get("ok").and_then(serde_json::Value::as_bool) != Some(true) {
            let error = value
                .get("error")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("unknown error");
            self.status = Some(format!("status: advance refused — {error}"));
            return;
        }
        let Some(tick) = value
            .pointer("/outcome/tick")
            .and_then(serde_json::Value::as_u64)
        else {
            // An ok-envelope without a readable outcome is a malformed
            // payload, never tick 0 (a fabricated counter is the exact
            // failure III.11 exists to forbid).
            self.status = Some("status: advance outcome UNREADABLE — malformed host data".into());
            return;
        };
        let paused = value
            .pointer("/outcome/paused")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(false);
        self.refresh_after_tick(tick);
        let suffix = if paused { " [PAUSED]" } else { "" };
        self.status = Some(format!("status: tick {tick}{suffix}"));
    }

    /// `r` — run until autopause/lock/limit (contract §1). The host call
    /// BLOCKS for the whole batch — zero incremental feedback is the
    /// Textual ground truth, not an oversight.
    fn cmd_run_until_paused(&mut self) {
        let snapshot = self.pacing_snapshot();
        if let Some(refusal) = Self::tick_refusal(&snapshot) {
            self.status = Some(format!("status: {refusal}"));
            return;
        }
        let raw = self.recording().run_until_paused();
        let value: serde_json::Value = match serde_json::from_str(&raw) {
            Ok(value) => value,
            Err(_) => {
                self.status =
                    Some("status: run_until_paused UNREADABLE — malformed host data".into());
                return;
            }
        };
        if value.get("ok").and_then(serde_json::Value::as_bool) != Some(true) {
            let error = value
                .get("error")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("unknown error");
            self.status = Some(format!("status: run refused — {error}"));
            return;
        }
        let Some(last_tick) = value
            .get("outcomes")
            .and_then(serde_json::Value::as_array)
            .and_then(|outcomes| outcomes.last())
            .and_then(|outcome| outcome.get("tick"))
            .and_then(serde_json::Value::as_u64)
        else {
            self.status = Some("status: run outcomes UNREADABLE — malformed host data".into());
            return;
        };
        self.refresh_after_tick(last_tick);
        // The post-run driver state picks the ending string (Textual's
        // three-way `app.py:2299-2309` readout).
        let after = self.pacing_snapshot();
        self.status = Some(if after.locked {
            let reason = after.lock_reason.as_deref().unwrap_or("unknown");
            format!("status: ran to tick {last_tick} — campaign ended ({reason})")
        } else if after.awaiting_ack {
            let summary = after.pause_summary.as_deref().unwrap_or("autopause");
            format!("status: ran to tick {last_tick} [PAUSED] ({summary})")
        } else {
            format!("status: ran to tick {last_tick} (stopped at the run limit)")
        });
    }

    /// `a` — acknowledge a pending autopause (contract §1).
    fn cmd_acknowledge_pause(&mut self) {
        let snapshot = self.pacing_snapshot();
        if snapshot.unreadable {
            self.status = Some(
                "status: pacing state UNREADABLE — malformed host data; refusing to \
                 acknowledge"
                    .to_string(),
            );
            return;
        }
        if !snapshot.awaiting_ack {
            self.status = Some("status: no autopause pending".to_string());
            return;
        }
        let raw = self.recording().acknowledge_pause();
        let ok = serde_json::from_str::<serde_json::Value>(&raw)
            .ok()
            .and_then(|v| v.get("ok").and_then(serde_json::Value::as_bool))
            .unwrap_or(false);
        if ok {
            // Refresh the HUD's PACING line immediately: the strip must
            // never keep claiming a pending autopause the driver just
            // cleared (verify-panel finding).
            let _ = self.pacing_snapshot();
        }
        self.status = Some(if ok {
            "status: autopause acknowledged — ready to advance".to_string()
        } else {
            let error = serde_json::from_str::<serde_json::Value>(&raw)
                .ok()
                .and_then(|v| {
                    v.get("error")
                        .and_then(serde_json::Value::as_str)
                        .map(str::to_string)
                })
                .unwrap_or_else(|| "unknown error".to_string());
            format!("status: acknowledge refused — {error}")
        });
    }

    /// F1–F9 — dispatch the verb at canonical slot `idx` (contract §3).
    /// The honest target is the current dossier subject's id-part ONLY when
    /// it is a real member of the row's `candidate_target_ids` — never
    /// invented (`_honest_target_id`, `app.py:707-739`).
    fn cmd_issue_verb(&mut self, idx: usize) {
        let Some(chrome) = self.chrome.as_ref() else {
            return;
        };
        if chrome.verbs.is_absent() {
            self.status = Some("status: no verb plate — no campaign bound".to_string());
            return;
        }
        if chrome.verbs.is_unreadable() {
            self.status = Some("status: verb plate UNREADABLE — malformed host data".to_string());
            return;
        }
        let Some(row) = chrome.verbs.row(idx) else {
            self.status = Some(format!(
                "status: F{} refused — verb missing from the plate",
                idx + 1
            ));
            return;
        };
        let verb = row.verb.clone();
        if !row.eligible {
            let reason = row
                .reason
                .clone()
                .unwrap_or_else(|| "ineligible".to_string());
            self.status = Some(format!("status: {verb} refused — {reason}"));
            return;
        }
        let afford_note = (!row.can_afford).then(|| row.afford_note.clone()).flatten();
        let target_id = self
            .views
            .iter()
            .find_map(|v| match v {
                View::Wiki(wiki) => wiki.current.clone(),
                View::Lobby(_) => None,
            })
            .map(|subject| match subject.split_once('/') {
                Some((_, id_part)) => id_part.to_string(),
                None => subject,
            })
            .filter(|id_part| row.candidate_target_ids.iter().any(|c| c == id_part));
        let args = serde_json::json!({
            "verb": verb,
            "target_id": target_id,
            "target_community": null,
        })
        .to_string();
        let raw = self.recording().issue_verb(&args);
        let value: serde_json::Value = match serde_json::from_str(&raw) {
            Ok(value) => value,
            Err(_) => {
                self.status = Some("status: issue_verb UNREADABLE — malformed host data".into());
                return;
            }
        };
        if value.get("ok").and_then(serde_json::Value::as_bool) == Some(true) {
            let turn_id = value
                .get("turn_id")
                .and_then(serde_json::Value::as_u64)
                .unwrap_or(0);
            let note = afford_note
                .map(|note| format!(" · {note}"))
                .unwrap_or_default();
            self.status = Some(format!("status: {verb} queued (turn #{turn_id}){note}"));
            // Textual refreshes the action bar alone on dispatch — effects
            // land at the NEXT tick, not now.
            let plate = self.recording().verb_plate_view_json();
            if let Some(chrome) = self.chrome.as_mut() {
                chrome.verbs = VerbPlateView::open(&plate);
            }
        } else {
            let error = value
                .get("error")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("unknown error");
            self.status = Some(format!("status: {verb} refused — {error}"));
        }
    }

    /// `P` (or `p` in the watchlist rail) — toggle a pin (contract §5).
    /// `subject_override` carries the rail's highlighted row; `None` pins
    /// the current dossier subject.
    fn cmd_toggle_pin(&mut self, subject_override: Option<String>) {
        let subject = subject_override.or_else(|| {
            self.views.iter().find_map(|v| match v {
                View::Wiki(wiki) => wiki.current.clone(),
                View::Lobby(_) => None,
            })
        });
        let Some(subject) = subject else {
            self.status = Some("status: nothing to pin — no subject open".to_string());
            return;
        };
        // Pin direction derives from the rail's rows — over an UNREADABLE
        // rail that derivation would silently claim "unpinned" and issue a
        // spurious pin write (verify-panel finding): refuse instead.
        if self
            .chrome
            .as_ref()
            .map(|chrome| chrome.watchlist.parse_failed)
            .unwrap_or(false)
        {
            self.status = Some("status: watchlist UNREADABLE — refusing pin writes".to_string());
            return;
        }
        let already_pinned = self
            .chrome
            .as_ref()
            .map(|chrome| {
                chrome.watchlist.rows.iter().any(|row| {
                    row.get("subject").and_then(serde_json::Value::as_str) == Some(&subject)
                })
            })
            .unwrap_or(false);
        let args = serde_json::json!({"subject": subject, "pinned": !already_pinned}).to_string();
        let raw = self.recording().pin_watchlist(&args);
        let ok = serde_json::from_str::<serde_json::Value>(&raw)
            .ok()
            .and_then(|v| v.get("ok").and_then(serde_json::Value::as_bool))
            .unwrap_or(false);
        if ok {
            let refreshed = self.recording().watchlist_json();
            if let Some(chrome) = self.chrome.as_mut() {
                let kept = chrome.watchlist.selected;
                chrome.watchlist = WatchlistView::open(&refreshed);
                chrome.watchlist.selected = kept.min(chrome.watchlist.rows.len().saturating_sub(1));
            }
            let action = if already_pinned { "unpinned" } else { "pinned" };
            self.status = Some(format!("status: {action} {subject}"));
        } else {
            let error = serde_json::from_str::<serde_json::Value>(&raw)
                .ok()
                .and_then(|v| {
                    v.get("error")
                        .and_then(serde_json::Value::as_str)
                        .map(str::to_string)
                })
                .unwrap_or_else(|| "unknown error".to_string());
            self.status = Some(format!("status: pin refused — {error}"));
        }
    }

    /// Refresh every chrome feed from the host (the post-bind pull and the
    /// tail of the post-tick fanout share this).
    fn refresh_chrome(&mut self) {
        if self.chrome.is_none() {
            return;
        }
        let endgame = self.recording().endgame_status_json();
        let pacing = self.recording().pacing_state_json();
        let plate = self.recording().verb_plate_view_json();
        let rail = self.recording().chronicle_rail_json();
        let watchlist = self.recording().watchlist_json();
        if let Some(chrome) = self.chrome.as_mut() {
            chrome.hud.update_endgame(&endgame);
            chrome.hud.update_pacing(&pacing);
            chrome.verbs = VerbPlateView::open(&plate);
            chrome.chronicle.update_from_json(&rail);
            // Highlight preservation across the rebuild (the Textual
            // `_refresh_watchlist` idiom: previous index, clamped).
            let kept = chrome.watchlist.selected;
            chrome.watchlist = WatchlistView::open(&watchlist);
            chrome.watchlist.selected = kept.min(chrome.watchlist.rows.len().saturating_sub(1));
        }
    }

    /// The post-tick refresh fanout, Textual's exact order (contract §6,
    /// `app.py:2102-2150`): (1) known subjects, (2) HUD, (3) verb plate,
    /// (4) chronicle, (5) watchlist, (6) re-fetch the open dossier WITHOUT
    /// switching views.
    fn refresh_after_tick(&mut self, tick: u64) {
        let raw = self.recording().known_subjects_json();
        let subjects: Vec<String> = serde_json::from_str(&raw).unwrap_or_default();
        self.known = Some(subjects.into_iter().collect());
        if let Some(chrome) = self.chrome.as_mut() {
            chrome.hud.set_tick(tick);
        }
        self.refresh_chrome();
        self.peek_cache = None; // a tick invalidates every cached stat plate
        let current = self.views.iter().find_map(|v| match v {
            View::Wiki(wiki) => wiki.current.clone(),
            View::Lobby(_) => None,
        });
        if let Some(subject) = current {
            let recording = RecordingHost {
                inner: &self.host,
                calls: &self.calls,
            };
            if let Some(View::Wiki(wiki)) =
                self.views.iter_mut().find(|v| matches!(v, View::Wiki(_)))
            {
                // Re-opening the current subject refreshes the page without
                // growing the jumplist (WikiView::open is idempotent for
                // the current subject).
                wiki.open(&BabylonTarget::Entity(subject), &recording);
            }
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
    if let Some(rest) = name.strip_prefix('f') {
        if let Ok(n) = rest.parse::<u8>() {
            if (1..=12).contains(&n) {
                return Some((KeyCode::F(n), KeyModifiers::NONE));
            }
        }
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
