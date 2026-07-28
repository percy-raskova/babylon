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
use crate::views::help::{HelpAction, HelpView};
use crate::views::hud::HudStrip;
use crate::views::keybar;
use crate::views::lobby::LobbyView;
use crate::views::msg::AppEvent;
use crate::views::palette::PaletteView;
use crate::views::peek::render_peek;
use crate::views::tutorial::TutorialOverlayView;
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

/// Which play-chrome pane the CENTER region shows (`1`/`2`/`3`/`4`;
/// contract §3). Only [`Pane::Wiki`] has a real renderer today — the other
/// three render an honest absence fence (the Textual P1 precedent: honest
/// `{absence}` fences until later programs wire the data), one line each.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Pane {
    /// The campaign dashboard (M4/M5 lands this surface).
    Dashboard,
    /// The map (M4/M5 lands this surface).
    Map,
    /// The Archive dossier — the only pane with a real renderer at M3.
    Wiki,
    /// The topology view (M4/M5 lands this surface).
    Topology,
}

impl Pane {
    /// The wire id `view_state.pane` reports (contract §1/§3) — the
    /// Textual `ContentSwitcher` ids verbatim.
    fn wire_id(self) -> &'static str {
        match self {
            Pane::Dashboard => "dashboard",
            Pane::Map => "map",
            Pane::Wiki => "wiki",
            Pane::Topology => "topology",
        }
    }
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
    /// The center region's current pane (contract §3); default `Wiki`.
    pane: Pane,
    /// The briefing-begin affordance's navigate-home target (contract §4),
    /// read off `load_campaign`'s ack `"home_subject"` field at bind time.
    home_subject: Option<String>,
    /// The topology pane (M4 contract §3: chrome-owned, never view-stacked).
    topology: crate::views::topology::TopologyView,
}

impl PlayChrome {
    fn new() -> Self {
        Self {
            hud: HudStrip::new(),
            chronicle: ChronicleRail::default(),
            verbs: VerbPlateView::open("null"),
            watchlist: WatchlistView::open("[]"),
            focus: ChromeFocus::Center,
            pane: Pane::Wiki,
            home_subject: None,
            topology: crate::views::topology::TopologyView::default(),
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

    fn tutorial_state_json(&self, view_state_json: &str) -> String {
        self.record("tutorial_state_json");
        self.inner.tutorial_state_json(view_state_json)
    }

    fn topology_json(&self, args_json: &str) -> String {
        self.record("topology_json");
        self.inner.topology_json(args_json)
    }

    fn field_state_json(&self) -> String {
        self.record("field_state_json");
        self.inner.field_state_json()
    }

    fn render_config_json(&self) -> String {
        self.record("render_config_json");
        self.inner.render_config_json()
    }

    fn new_campaign(&self) -> String {
        self.record("new_campaign");
        self.inner.new_campaign()
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
    /// The `?` help overlay (Wave 1 §3); `Some` while open — the palette
    /// field precedent, NOT a view-stack entry (recorded deviation).
    help: Option<HelpView>,
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
    /// The tutorial overlay's last-polled state (contract §1); the default
    /// `active: false` view renders nothing, so a tutorial-disabled or
    /// not-yet-bound session shows no strip.
    tutorial: TutorialOverlayView,
    /// `true` once the player has dismissed the tutorial strip for this
    /// session (`Esc` while it is visible) — reset on every fresh bind
    /// (contract §1's per-`bind_session` reset, the M2 `_chronicle_history`
    /// precedent).
    tutorial_dismissed: bool,
    /// `true` when something that could change [`Self::poll_tutorial`]'s
    /// predicate inputs (the open subject, the pane, `chrome_verbs`) has
    /// happened since the last poll (R13b fix): set after a fresh bind,
    /// after every [`Self::handle_key`] call, after a mouse LEFT-click
    /// (never a bare hover-`Moved`), and after
    /// [`Self::refresh_after_tick`] — [`Self::poll_tutorial`] consumes it,
    /// so a bare resize redraw between real inputs never re-crosses the
    /// FFI seam for nothing.
    tutorial_poll_pending: bool,
    /// The client's cumulative chrome-dispatch log (contract §1): appended
    /// once per verb name, never duplicated. Only `"peek_wikilink"` is ever
    /// appended in this milestone — host-side material verbs are the
    /// host's own log, not the client's to report.
    chrome_verbs: Vec<String>,
    /// `true` while the terminal is below the declared 100×24 floor
    /// (Wave 1 contract §1, Director ruling 1) — set by every
    /// [`Self::render_frame`], read by the input handlers so no key or
    /// click mutates state against an invisible UI (only the quit set
    /// passes through).
    floor_guard_active: bool,
}

/// The declared minimum terminal width (Wave 1 contract §1, ruling 1).
/// Display constants, not `GameDefines` — no gameplay meaning (the
/// `PAGE_SCROLL` precedent). Density is DESIGNED to 100×30 (the recon
/// arithmetic of record: there the verb plate fits even with the
/// tutorial strip at its full 40% ceiling), but the GUARD floor is
/// lower: the Director's 2026-07-28 field report — a fullscreen 151×27
/// laptop terminal locked out of the game entirely — ruled the 30-row
/// floor too aggressive for real hardware. The §1 invariant (the verb
/// plate never clips) is re-established at every admitted height by
/// clamping the tutorial strip band against `PLAY_CHROME_MIN_ROWS`
/// (private, this module) instead: the strip (compressible prose)
/// yields, the plate never does.
pub const FLOOR_WIDTH: u16 = 100;
/// The declared minimum terminal height (see [`FLOOR_WIDTH`]): the
/// classic 24-row terminal floor.
pub const FLOOR_HEIGHT: u16 = 24;

/// The play chrome's fixed vertical budget below the tutorial strip:
/// HUD 3 + mid-region minimum 5 + verb plate 8 + status 1 + keybar 1.
/// The strip band is clamped to `height − PLAY_CHROME_MIN_ROWS` so these
/// rows survive at every height the floor guard admits (≥ 6 strip rows
/// remain at the 24-row floor).
const PLAY_CHROME_MIN_ROWS: u16 = 18;

/// Render the too-small notice — the ONLY surface below the floor.
fn render_floor_notice(frame: &mut ratatui::Frame<'_>, area: Rect, width: u16, height: u16) {
    use ratatui::style::{Modifier, Style};
    use ratatui::text::Line;
    use ratatui::widgets::Paragraph;

    let lines = vec![
        Line::from("▌ terminal too small".to_string()).style(
            Style::new()
                .fg(crate::theme::CRIMSON)
                .add_modifier(Modifier::BOLD),
        ),
        Line::from(format!(
            "{width}x{height} now — the Archive needs at least {FLOOR_WIDTH}x{FLOOR_HEIGHT}"
        ))
        .style(Style::new().fg(crate::theme::BONE)),
        Line::from("resize to continue — q quits".to_string())
            .style(Style::new().fg(crate::theme::DIM)),
    ];
    // Vertically center the three lines; Paragraph clips gracefully when
    // the terminal is too small even for the notice itself.
    let top = (area.height.saturating_sub(3)) / 2;
    let band = Rect {
        x: area.x,
        y: area.y + top,
        width: area.width,
        height: area.height.saturating_sub(top).min(3),
    };
    frame.render_widget(Paragraph::new(lines).centered(), band);
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
            help: None,
            registry: LayoutRegistry::new(),
            known: None,
            peek_target: None,
            peek_depth: 0,
            peek_cache: None,
            chrome: None,
            status: None,
            tutorial: TutorialOverlayView::default(),
            tutorial_dismissed: false,
            tutorial_poll_pending: false,
            chrome_verbs: Vec::new(),
            floor_guard_active: false,
        }
    }

    /// Host-method names invoked so far, in call order.
    pub fn host_calls(&self) -> Vec<String> {
        self.calls.borrow().clone()
    }

    /// Drain the host-call log, returning everything recorded since the
    /// last drain (or since [`Self::new`]) and leaving it empty.
    /// `run_interactive`'s own per-iteration call (R13b note): its
    /// transcript is discarded at quit (`"frames": []` in the FFI JSON),
    /// so the log must never accumulate for an entire play session's
    /// lifetime — headless replay is the sole caller that needs the FULL,
    /// undrained history, via [`Self::host_calls`].
    pub fn drain_host_calls(&self) -> Vec<String> {
        std::mem::take(&mut *self.calls.borrow_mut())
    }

    /// The wrapped host (integration tests inspect their stateful fakes
    /// through this; production callers never need it).
    pub fn host_ref(&self) -> &H {
        &self.host
    }

    /// The client's cumulative chrome-dispatch log (contract §1) —
    /// integration tests inspect it through this; production callers never
    /// need it.
    pub fn chrome_verbs(&self) -> &[String] {
        &self.chrome_verbs
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

    /// Pre-fetch the tutorial overlay's state outside the draw closure (the
    /// `peek_json` idiom, contract §1) — the HOST is the sole arming
    /// authority (`{"active": false}` renders nothing); `tutorial_enabled`
    /// and `!tutorial_dismissed` are seam-crossing savers on top of it,
    /// both honest about which layer decided. A no-op while no campaign is
    /// bound, tutorials are disabled for this run, or the player already
    /// dismissed the strip this session.
    ///
    /// R13b fix (verify-panel finding): gated on and consuming
    /// [`Self::tutorial_poll_pending`] first — polling every single frame
    /// crossed the FFI seam even on a bare resize redraw with nothing that
    /// could have changed the predicate inputs; the flag is set wherever
    /// those inputs actually can move (bind, every key, mouse clicks, the
    /// post-tick refresh), so headless replay (every script entry is a key
    /// or click) still polls exactly once per post-bind frame, unchanged.
    fn poll_tutorial(&mut self) {
        if !self.tutorial_poll_pending {
            return;
        }
        self.tutorial_poll_pending = false;
        if !self.cfg.tutorial_enabled || self.tutorial_dismissed {
            return;
        }
        let Some(chrome) = self.chrome.as_ref() else {
            return;
        };
        let pane = chrome.pane.wire_id();
        let subject = self.views.iter().find_map(|v| match v {
            View::Wiki(wiki) => wiki.current.clone(),
            View::Lobby(_) => None,
        });
        // Field order pinned (contract §1): subject, pane, chrome_verbs.
        let view_state = serde_json::json!({
            "subject": subject,
            "pane": pane,
            "chrome_verbs": self.chrome_verbs.clone(),
        })
        .to_string();
        let raw = self.recording().tutorial_state_json(&view_state);
        self.tutorial.update_from_json(&raw);
    }

    /// Whether the tutorial strip is currently on screen: a campaign is
    /// bound (R2 fix — the strip can never outlive the chrome that
    /// reserves its band), armed (`active`, including the finished state)
    /// or loudly UNREADABLE, and not yet dismissed for this session
    /// (contract §1's `Esc` precedence).
    fn tutorial_visible(&self) -> bool {
        self.chrome.is_some()
            && !self.tutorial_dismissed
            && (self.tutorial.active || self.tutorial.parse_failed)
    }

    /// Append `verb` to the chrome-dispatch log if not already present
    /// (append-once per name, contract §1's `chrome_verbs`) — cumulative
    /// for the bound session, reset on the next bind.
    fn record_chrome_verb(&mut self, verb: &str) {
        if !self.chrome_verbs.iter().any(|v| v == verb) {
            self.chrome_verbs.push(verb.to_string());
        }
    }

    /// Render one frame into `terminal`.
    ///
    /// ratatui 0.30 gives `Backend` an associated `Error` type, so this
    /// returns `Result<(), B::Error>` (the plan's `io::Result` was the
    /// 0.29-era shape of the same contract).
    pub fn render_frame<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> Result<(), B::Error> {
        self.ensure_root();
        // The 100×24 floor guard (Wave 1 contract §1, ruling 1): below the
        // declared floor NOTHING but the notice renders and the input
        // handlers swallow everything outside the quit set — the layout
        // arithmetic below the floor cannibalizes real chrome (the verb
        // plate loses three Article-V verbs at 80×24), and a UI the
        // player cannot see must not mutate under them.
        let size = terminal.size()?;
        self.floor_guard_active = size.width < FLOOR_WIDTH || size.height < FLOOR_HEIGHT;
        if self.floor_guard_active {
            terminal.draw(|frame| {
                render_floor_notice(frame, frame.area(), size.width, size.height);
            })?;
            return Ok(());
        }
        self.poll_tutorial();
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
        let tutorial_visible = self.tutorial_visible();
        let title = format!("The Archive — {}", self.cfg.campaign_name);
        let known = self.known.clone().unwrap_or_default();
        let views = &mut self.views;
        let registry = &mut self.registry;
        let palette = &self.palette;
        let help = &self.help;
        let peek_depth = self.peek_depth;
        let chrome = &mut self.chrome;
        let status = self.status.clone();
        let tutorial = &self.tutorial;
        terminal.draw(|frame| {
            registry.clear();
            let area = frame.area();
            // Wave 1: derive the active surface ONCE (a short-lived &mut
            // borrow for the topology mode), shared by the keybar bands
            // and the help overlay's mode-scoped section.
            let surface_now = match (views.last(), chrome.as_mut()) {
                (Some(View::Wiki(_)), Some(c)) => {
                    if palette.is_some() {
                        keybar::KeybarSurface::Overlay
                    } else {
                        match c.focus {
                            ChromeFocus::Watchlist => {
                                keybar::KeybarSurface::Rail { watchlist: true }
                            }
                            ChromeFocus::Chronicle => {
                                keybar::KeybarSurface::Rail { watchlist: false }
                            }
                            ChromeFocus::Center => match c.pane {
                                Pane::Wiki => keybar::KeybarSurface::Wiki,
                                Pane::Dashboard | Pane::Map => keybar::KeybarSurface::AbsencePane,
                                Pane::Topology => {
                                    if c.topology.mode()
                                        == crate::views::topology::TopologyMode::Glyph2d
                                    {
                                        keybar::KeybarSurface::TopologyGlyph
                                    } else {
                                        keybar::KeybarSurface::Topology3d
                                    }
                                }
                            },
                        }
                    }
                }
                (Some(View::Lobby(_)), _) => {
                    if palette.is_some() {
                        keybar::KeybarSurface::Overlay
                    } else {
                        keybar::KeybarSurface::Lobby
                    }
                }
                _ => keybar::KeybarSurface::BareWiki,
            };
            match (views.last_mut(), chrome.as_mut()) {
                // The play screen (design §7): HUD top, watchlist rail LEFT,
                // wiki center, chronicle rail RIGHT, verb plate BOTTOM, one
                // status line.
                (Some(View::Wiki(wiki)), Some(chrome)) => {
                    // The tutorial strip, when visible, RESERVES its own
                    // band at the top of the play area FIRST — Textual
                    // dock semantics (reserve, push down), never
                    // Clear-over (R1 fix, a verify-panel blocker: the
                    // strip previously overlaid the whole chrome layout
                    // below it instead of making room, which also let
                    // clicks reach entities the strip visually covered,
                    // since the wiki laid out its link-hit rects against
                    // the FULL area).
                    let (strip_area, chrome_area) = if tutorial_visible {
                        // Clamped so the fixed chrome below always keeps its
                        // rows — the strip yields, the verb plate never
                        // clips (the §1 invariant at the 24-row floor).
                        let strip_height = tutorial
                            .height_for(area.width, area.height)
                            .min(area.height.saturating_sub(PLAY_CHROME_MIN_ROWS));
                        let [strip_area, chrome_area] = Layout::vertical([
                            Constraint::Length(strip_height),
                            Constraint::Min(0),
                        ])
                        .areas(area);
                        (Some(strip_area), chrome_area)
                    } else {
                        (None, area)
                    };
                    // Wave 1 §2: the keybar takes the LAST one-line band;
                    // the elastic mid region pays the row (the status-line
                    // mechanism, one row deeper).
                    let [hud_area, mid_area, plate_area, status_area, keybar_area] =
                        Layout::vertical([
                            Constraint::Length(3),
                            Constraint::Min(5),
                            Constraint::Length(8),
                            Constraint::Length(1),
                            Constraint::Length(1),
                        ])
                        .areas(chrome_area);
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
                        registry,
                    );
                    // Wave 1 §5: the center region is hit-testable for
                    // wheel routing (link/verb hits stay innermost-wins;
                    // region_at ignores them by construction).
                    registry.register(
                        crate::layout_registry::WidgetId(3002),
                        center_area,
                        Some("region:center".to_string()),
                    );
                    // Center region: only the wiki pane has a real
                    // renderer at M3 (contract §3) — the other three show
                    // an honest absence fence, one line each, rather than
                    // a fabricated surface.
                    match chrome.pane {
                        Pane::Wiki => wiki.render(frame, center_area, registry, &known),
                        Pane::Dashboard => render_pane_absence(frame, center_area, DASHBOARD_FENCE),
                        Pane::Map => render_pane_absence(frame, center_area, MAP_FENCE),
                        // M4: the topology pane is real (contract §3) —
                        // 3D lane by default, glyph floor one 'g' away.
                        Pane::Topology => chrome.topology.render(frame, center_area),
                    }
                    chrome.chronicle.render(
                        frame,
                        chron_area,
                        chrome.focus == ChromeFocus::Chronicle,
                        registry,
                    );
                    chrome.verbs.render(frame, plate_area, registry);
                    if let Some(text) = &status {
                        frame.render_widget(ratatui::text::Line::from(text.as_str()), status_area);
                    }
                    keybar::render_keybar(frame, keybar_area, surface_now, registry);
                    if let Some(strip_area) = strip_area {
                        tutorial.render(frame, strip_area);
                    }
                }
                (Some(View::Lobby(lobby)), _) => {
                    // Wave 1 §2: the lobby always reserves the keybar row;
                    // the status band only when there is a status.
                    if let Some(text) = &status {
                        let [lobby_area, status_area, keybar_area] = Layout::vertical([
                            Constraint::Min(3),
                            Constraint::Length(1),
                            Constraint::Length(1),
                        ])
                        .areas(area);
                        lobby.render(frame, lobby_area);
                        frame.render_widget(ratatui::text::Line::from(text.as_str()), status_area);
                        keybar::render_keybar(frame, keybar_area, surface_now, registry);
                    } else {
                        let [lobby_area, keybar_area] =
                            Layout::vertical([Constraint::Min(3), Constraint::Length(1)])
                                .areas(area);
                        lobby.render(frame, lobby_area);
                        keybar::render_keybar(frame, keybar_area, surface_now, registry);
                    }
                }
                (Some(View::Wiki(wiki)), None) => {
                    // The chrome-less failure page gains the keybar band it
                    // never had (Wave 1 §2: every screen has one).
                    let [wiki_area, keybar_area] =
                        Layout::vertical([Constraint::Min(3), Constraint::Length(1)]).areas(area);
                    wiki.render(frame, wiki_area, registry, &known);
                    keybar::render_keybar(
                        frame,
                        keybar_area,
                        keybar::KeybarSurface::BareWiki,
                        registry,
                    );
                }
                (None, _) => unreachable!("ensure_root always seeds the lobby"),
            }
            // Z-order (contract §1): the tutorial strip is now a RESERVED
            // band inside the play-screen branch above (R1: reserve, push
            // down — never an overlay), so only the palette and peek
            // remain as overlays on top of whatever base layout (chrome or
            // lobby) rendered into `area`.
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
            // Wave 1 §3: the help plate paints over everything (it is the
            // only overlay that can be open — '?' types into an open
            // palette rather than reaching the global arm).
            if let Some(help) = help {
                help.render(frame, area, surface_now);
            }
            let _ = title; // chrome title is owned by each view's block (M1)
        })?;
        Ok(())
    }

    /// Handle one key event. Returns `true` when the app should quit.
    pub fn handle_key(&mut self, code: KeyCode, modifiers: KeyModifiers) -> bool {
        // The floor guard swallows everything except the quit set (Wave 1
        // contract §1): the UI is invisible below the floor, so no key may
        // mutate state under it. Checked BEFORE the tutorial-poll flag —
        // a swallowed key is not a predicate input either.
        if self.floor_guard_active {
            return matches!(code, KeyCode::Char('q') | KeyCode::Esc)
                || (code == KeyCode::Char('c') && modifiers.contains(KeyModifiers::CONTROL));
        }
        // R13b fix: ANY key could move a tutorial predicate input (the
        // open subject, the pane, `chrome_verbs`) regardless of which arm
        // below ends up handling it — set the poll-pending flag
        // unconditionally, up front, rather than duplicating it at every
        // one of this function's many early returns.
        self.tutorial_poll_pending = true;
        // Help is modal (Wave 1 §3, the palette precedent): it sees every
        // key while open; only its close set escapes it.
        if let Some(help) = &mut self.help {
            if help.handle_key(code) == HelpAction::Close {
                self.help = None;
            }
            return false;
        }
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
        // Tutorial dismiss (contract §1): while the strip is genuinely
        // ACTIVE (including the finished state, which still carries
        // `active: true`), Esc dismisses it for the session and is
        // consumed here, AHEAD of the rail-defocus/view fallthrough below
        // (RECORDED DEVIATION: Textual keeps its `dismissed` flag on the
        // overlay widget; here it lives on `App` — observably identical,
        // permanent for the session). R12 fix (verify-panel finding, x2):
        // the loud UNREADABLE strip is deliberately EXCLUDED here — a
        // malformed payload is a live error the strip must keep showing
        // (and `poll_tutorial` must keep polling for) until a recovered
        // host clears it, never something a stray Esc can wave away.
        if code == KeyCode::Esc && self.tutorial.active && !self.tutorial.parse_failed {
            self.tutorial_dismissed = true;
            return false;
        }
        // Global bindings (Task 19): palette, peek, view-switch scaffold.
        match code {
            // Wave 1 §3: '?' opens the mode-scoped help overlay from ANY
            // surface (after the palette interception above, so '?' still
            // types into an open palette query).
            KeyCode::Char('?') => {
                self.help = Some(HelpView::default());
                return false;
            }
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
                if self.chrome.is_some() {
                    // Dispatch proof (contract §1/§4): the press reached
                    // the peek dispatch regardless of outcome.
                    self.record_chrome_verb("peek_wikilink");
                    // R16 fix (verify-panel finding): a stale peek target
                    // surviving a pane switch away from Wiki must not
                    // resurrect the peek overlay over the dashboard/map/
                    // topology absence fences — same refusal string as
                    // "nothing to peek", since from the player's
                    // perspective there IS nothing peekable there.
                    let on_wiki = self
                        .chrome
                        .as_ref()
                        .is_some_and(|chrome| chrome.pane == Pane::Wiki);
                    if !on_wiki || self.peek_target.is_none() {
                        self.status = Some("status: no wikilinks to peek on this page".to_string());
                        return false;
                    }
                }
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
            // Wave 1 §4: Shift-Tab is Tab's exact mirror (crossterm reports
            // it as the distinct BackTab code in legacy parsing mode; the
            // recon confirmed it reached this handler and was swallowed by
            // the view catch-alls).
            KeyCode::BackTab if self.chrome.is_some() => {
                if let Some(chrome) = self.chrome.as_mut() {
                    chrome.focus = match chrome.focus {
                        ChromeFocus::Center => ChromeFocus::Watchlist,
                        ChromeFocus::Watchlist => ChromeFocus::Chronicle,
                        ChromeFocus::Chronicle => ChromeFocus::Center,
                    };
                }
                return false;
            }
            // '1'/'2'/'3'/'4' switch the play-chrome pane AND return focus
            // to Center (contract §3 — mirrors the Textual shell's
            // dashboard/map/wiki/topology order). `3`'s M2 focus-only
            // meaning is SUBSUMED: it now also (re)selects the wiki pane.
            KeyCode::Char(c @ ('1' | '2' | '3' | '4')) if self.chrome.is_some() => {
                if let Some(chrome) = self.chrome.as_mut() {
                    chrome.pane = match c {
                        '1' => Pane::Dashboard,
                        '2' => Pane::Map,
                        '4' => Pane::Topology,
                        _ => Pane::Wiki, // '3'
                    };
                    chrome.focus = ChromeFocus::Center;
                }
                // R16 fix (verify-panel finding): a peek target/cache from
                // the wiki pane must not survive a switch to a pane that
                // isn't Wiki at all — the peek overlay has no meaning over
                // the dashboard/map/topology absence fences.
                if self
                    .chrome
                    .as_ref()
                    .is_some_and(|chrome| chrome.pane != Pane::Wiki)
                {
                    self.peek_target = None;
                    self.peek_cache = None;
                }
                // M4: entering the topology pane pulls its payloads.
                if self
                    .chrome
                    .as_ref()
                    .is_some_and(|chrome| chrome.pane == Pane::Topology)
                {
                    self.refresh_topology();
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
            // Esc defocuses a rail back to the center — it never falls
            // through to the wiki's own Esc=Back arm, which would pop the
            // view and read as campaign teardown (the M2 contract promised
            // this arm and the rails' own doc comments assert it; the arm
            // itself was missing until M3 — found by the M3 port's own
            // firsthand read, fixed here). Runs AFTER the tutorial-dismiss
            // Esc check above, per the M3 §1 precedence chain.
            Some(chrome) if chrome.focus != ChromeFocus::Center && code == KeyCode::Esc => {
                chrome.focus = ChromeFocus::Center;
                RailAction::Handled
            }
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
        // M4: topology-pane keys (contract §6 + the 'g' cycle) — MUST
        // precede the wiki fallthrough, which otherwise consumes the
        // arrows/chars regardless of the active pane (the recon's
        // match-arm-order trap).
        if self
            .chrome
            .as_ref()
            .is_some_and(|c| c.pane == Pane::Topology && c.focus == ChromeFocus::Center)
        {
            use crate::views::topology::TopologyAction;
            // Esc leaves the pane back to the wiki (verify-panel finding:
            // it used to fall through and tear the campaign down — 'leave
            // this pane' and 'leave the campaign' are different verbs).
            if code == KeyCode::Esc {
                if let Some(chrome) = self.chrome.as_mut() {
                    chrome.pane = Pane::Wiki;
                }
                return false;
            }
            let action = self
                .chrome
                .as_mut()
                .map(|c| c.topology.handle_key(code))
                .unwrap_or(TopologyAction::NotHandled);
            match action {
                TopologyAction::Handled => return false,
                TopologyAction::NeedsRefresh => {
                    self.refresh_topology();
                    return false;
                }
                TopologyAction::NotHandled => {}
            }
        }
        let ev = match self.views.last_mut() {
            Some(View::Lobby(lobby)) => lobby.handle_key(code),
            Some(View::Wiki(wiki)) => {
                let event = wiki.handle_key(code, modifiers);
                // Briefing begin (contract §4): Enter with NO link under
                // the cursor (the only way `WikiView::handle_key`'s own
                // Enter arm returns `None`) while the current subject is a
                // briefing page navigates home — the composition-level
                // affordance Textual implements as `BriefingScreen`'s
                // Enter→dismiss→`_navigate(_SAMPLE_SUBJECT)`. The baked
                // briefing page itself carries ZERO wikilinks, so an
                // Enter-on-link mapping is impossible; this is the honest
                // port.
                if event.is_none() && code == KeyCode::Enter {
                    self.chrome
                        .as_ref()
                        .and_then(|chrome| chrome.home_subject.clone())
                        .filter(|_| {
                            wiki.current
                                .as_deref()
                                .is_some_and(|subject| subject.starts_with("briefing/"))
                        })
                        .map(AppEvent::OpenSubject)
                } else {
                    event
                }
            }
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
        // Floor guard (Wave 1 contract §1): no click may mutate state
        // against the invisible UI.
        if self.floor_guard_active {
            return false;
        }
        match ev.kind {
            MouseEventKind::Moved => {
                self.peek_target = self
                    .registry
                    .hit(ev.column, ev.row)
                    .and_then(|(_, _, entity)| entity.clone())
                    // Verb rows and keybar cells are dispatch zones, not
                    // peekable entities — nor are rail rows/region rects.
                    .filter(|entity| {
                        !entity.starts_with("verb:")
                            && !entity.starts_with("key:")
                            && !entity.starts_with("region:")
                            && !entity.starts_with("watchlist:")
                            && !entity.starts_with("chronicle:")
                    });
            }
            MouseEventKind::Down(MouseButton::Left) => {
                // R13b fix: a click (never a bare hover-`Moved`) could
                // move a tutorial predicate input just like a key press.
                self.tutorial_poll_pending = true;
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
                    // Wave 1 §2: a keybar cell routes through the SAME
                    // handle_key path its key uses — one routing
                    // authority, never a second dispatch table.
                    if let Some(name) = subject.strip_prefix("key:") {
                        return match key_event_from_name(name) {
                            Some((code, modifiers)) => self.handle_key(code, modifiers),
                            None => false,
                        };
                    }
                    // Wave 1 §5: rail rows — first click focuses the rail
                    // AND selects the clicked row; a second click on the
                    // already-selected row opens it (Enter through the
                    // rail's own handler — one routing authority).
                    if let Some(raw) = subject.strip_prefix("watchlist:") {
                        if let (Some(index), Some(chrome)) =
                            (raw.parse::<usize>().ok(), self.chrome.as_mut())
                        {
                            let reopen = chrome.focus == ChromeFocus::Watchlist
                                && chrome.watchlist.selected == index;
                            chrome.focus = ChromeFocus::Watchlist;
                            chrome.watchlist.selected = index;
                            if reopen {
                                if let Some(ev) = chrome.watchlist.handle_key(KeyCode::Enter) {
                                    chrome.focus = ChromeFocus::Center;
                                    return self.route(ev);
                                }
                            }
                        }
                        return false;
                    }
                    if let Some(raw) = subject.strip_prefix("chronicle:") {
                        if let (Some(index), Some(chrome)) =
                            (raw.parse::<usize>().ok(), self.chrome.as_mut())
                        {
                            let reopen = chrome.focus == ChromeFocus::Chronicle
                                && chrome.chronicle.cursor == Some(index);
                            chrome.focus = ChromeFocus::Chronicle;
                            chrome.chronicle.cursor = Some(index);
                            if reopen {
                                if let Some(ev) = chrome.chronicle.handle_key(KeyCode::Enter) {
                                    chrome.focus = ChromeFocus::Center;
                                    return self.route(ev);
                                }
                            }
                        }
                        return false;
                    }
                    // A click on a rail's empty area (the region rect, no
                    // row under it) still focuses the rail (D3: "a click
                    // on a rail doesn't even focus it").
                    match subject.as_str() {
                        "region:watchlist" => {
                            if let Some(chrome) = self.chrome.as_mut() {
                                chrome.focus = ChromeFocus::Watchlist;
                            }
                            return false;
                        }
                        "region:chronicle" => {
                            if let Some(chrome) = self.chrome.as_mut() {
                                chrome.focus = ChromeFocus::Chronicle;
                            }
                            return false;
                        }
                        "region:center" => {
                            if let Some(chrome) = self.chrome.as_mut() {
                                chrome.focus = ChromeFocus::Center;
                            }
                            return false;
                        }
                        _ => {}
                    }
                    return self.route(AppEvent::OpenSubject(subject));
                }
            }
            // Wave 1 §5: the wheel routes by REGION (never innermost-wins
            // — a link under the cursor must not swallow the scroll) and
            // synthesizes the region's own keys: one routing authority.
            MouseEventKind::ScrollUp | MouseEventKind::ScrollDown => {
                let down = ev.kind == MouseEventKind::ScrollDown;
                let region = self
                    .registry
                    .region_at(ev.column, ev.row)
                    .map(str::to_string);
                match region.as_deref() {
                    Some("region:center") => {
                        if let Some(chrome) = self.chrome.as_mut() {
                            match chrome.pane {
                                Pane::Wiki => {
                                    // ±3 rows per notch, through the wiki's
                                    // own Up/Down handling (clamped there).
                                    if let Some(View::Wiki(wiki)) = self.views.last_mut() {
                                        let code = if down { KeyCode::Down } else { KeyCode::Up };
                                        for _ in 0..3 {
                                            let _ = wiki.handle_key(code, KeyModifiers::NONE);
                                        }
                                    }
                                }
                                Pane::Topology => {
                                    // Glyph floor scrolls; 3D zooms (the
                                    // wheel IS the zoom affordance there).
                                    let code = match chrome.topology.mode() {
                                        crate::views::topology::TopologyMode::Glyph2d => {
                                            if down {
                                                KeyCode::Down
                                            } else {
                                                KeyCode::Up
                                            }
                                        }
                                        _ => {
                                            if down {
                                                KeyCode::Char('-')
                                            } else {
                                                KeyCode::Char('+')
                                            }
                                        }
                                    };
                                    let _ = chrome.topology.handle_key(code);
                                }
                                Pane::Dashboard | Pane::Map => {}
                            }
                        }
                    }
                    Some("region:watchlist") => {
                        if let Some(chrome) = self.chrome.as_mut() {
                            chrome.focus = ChromeFocus::Watchlist;
                            let code = if down { KeyCode::Down } else { KeyCode::Up };
                            let _ = chrome.watchlist.handle_key(code);
                        }
                    }
                    Some("region:chronicle") => {
                        if let Some(chrome) = self.chrome.as_mut() {
                            chrome.focus = ChromeFocus::Chronicle;
                            let code = if down { KeyCode::Down } else { KeyCode::Up };
                            let _ = chrome.chronicle.handle_key(code);
                        }
                    }
                    _ => {}
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
            // Wave 1 §5: wheel behavior is transcript-testable.
            ScriptStep::Scroll {
                scroll: (col, row),
                direction,
            } => self.handle_mouse(MouseEvent {
                kind: match direction {
                    crate::config::ScrollDirection::Up => MouseEventKind::ScrollUp,
                    crate::config::ScrollDirection::Down => MouseEventKind::ScrollDown,
                },
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
                // The briefing-begin affordance's navigate-home target
                // (contract §4), sourced from the ack's `"home_subject"`.
                let home_subject = serde_json::from_str::<serde_json::Value>(&ack)
                    .ok()
                    .and_then(|v| {
                        v.get("home_subject")
                            .and_then(serde_json::Value::as_str)
                            .map(str::to_string)
                    });
                let mut chrome = PlayChrome::new();
                chrome.hud.set_tick(tick);
                chrome.home_subject = home_subject;
                // Task 35 (contract §7): read the recorded [render] verdict
                // ONCE, at bind — `babylon doctor` probed it; the client
                // honors the record and never re-probes (ADR097 D4). Goes
                // through the recording seam so the transcript's host-call
                // log attests the read like every other host touch.
                chrome.topology.render_settings = crate::config::RenderSettings::from_json(
                    &self.recording().render_config_json(),
                );
                self.chrome = Some(chrome);
                // Tutorial arming state resets on every bind (the M2
                // `_chronicle_history` precedent): a new campaign's
                // tutorial must never inherit a previous session's
                // dismissal or verb-dispatch log.
                self.tutorial = TutorialOverlayView::default();
                self.tutorial_dismissed = false;
                self.chrome_verbs = Vec::new();
                // R13b fix: a fresh bind is a predicate-input change (the
                // subject, the pane) just like a key press or a tick.
                self.tutorial_poll_pending = true;
                self.refresh_chrome();
                false
            }
            // The lobby `n` mint (contract §2): mint, then re-pull the
            // catalog and highlight the minted row by `campaign_id`.
            // Catalog failures are system-level and panic inside the host
            // itself (III.11) — the two `ok: false` branches below handle
            // only the seam's own honest-refusal shapes (the default
            // not-implemented envelope, and a malformed ok-envelope), never
            // a fabricated success.
            AppEvent::NewCampaign => {
                let raw = self.recording().new_campaign();
                let value: serde_json::Value = match serde_json::from_str(&raw) {
                    Ok(value) => value,
                    Err(_) => {
                        self.status =
                            Some("status: new_campaign UNREADABLE — malformed host data".into());
                        return false;
                    }
                };
                if value.get("ok").and_then(serde_json::Value::as_bool) != Some(true) {
                    let error = value
                        .get("error")
                        .and_then(serde_json::Value::as_str)
                        .unwrap_or("unknown error");
                    self.status = Some(format!("status: new campaign refused — {error}"));
                    return false;
                }
                let campaign_id = value.get("campaign_id").and_then(serde_json::Value::as_str);
                let codename = value.get("codename").and_then(serde_json::Value::as_str);
                let (Some(campaign_id), Some(codename)) = (campaign_id, codename) else {
                    self.status = Some(
                        "status: new_campaign ok-envelope UNREADABLE — malformed host data".into(),
                    );
                    return false;
                };
                let (campaign_id, codename) = (campaign_id.to_string(), codename.to_string());
                let catalog_raw = self.recording().lobby_catalog_json();
                let mut lobby = LobbyView::from_catalog_json(&catalog_raw);
                // R15 fix (verify-panel finding): a minted campaign absent
                // from the very catalog pull meant to carry it is a loud
                // contract violation, never something the client papers
                // over by guessing row 0 as the new selection.
                let previous_selected = match self.views.last() {
                    Some(View::Lobby(existing)) => existing.selected,
                    _ => 0,
                };
                match lobby
                    .rows
                    .iter()
                    .position(|row| row.campaign_id == campaign_id)
                {
                    Some(index) => {
                        lobby.selected = index;
                        self.status = Some(format!(
                            "status: minted Operation {codename} — press Enter to load"
                        ));
                    }
                    None => {
                        lobby.selected = previous_selected.min(lobby.rows.len().saturating_sub(1));
                        self.status = Some(format!(
                            "status: minted Operation {codename}, but the catalog did not \
                             return it — refusing to guess a row"
                        ));
                    }
                }
                if let Some(View::Lobby(existing)) = self.views.last_mut() {
                    *existing = lobby;
                }
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
                // Every subject-open navigation forces the wiki pane
                // (contract §3) — rail Enter, palette pick, wikilink open,
                // and briefing-begin all funnel through this arm.
                if let Some(chrome) = self.chrome.as_mut() {
                    chrome.pane = Pane::Wiki;
                }
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
                        // R2 fix (verify-panel finding): reset the
                        // tutorial arming state exactly like the
                        // fresh-bind reset above — otherwise a dismissed
                        // or mid-arc tutorial would silently carry into
                        // the NEXT campaign bound this session, and
                        // `tutorial_visible()` would keep reporting a
                        // strip with no chrome left to reserve a band for.
                        self.tutorial = TutorialOverlayView::default();
                        self.tutorial_dismissed = false;
                        self.chrome_verbs.clear();
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
            // R4 fix (verify-panel major finding): the ACTIONABLE
            // instruction goes FIRST — a real Wayne tick lists 4+ critical
            // event types, and the old summary-first order pushed "press
            // 'a' to acknowledge" past the right edge on narrower terminals
            // (found by the M3 parity harness against real engine output —
            // the instruction, not the inventory, is what the refusal
            // exists to deliver). The summary now rides at the tail, where
            // a narrow terminal's natural left-to-right clip only trims
            // supplementary detail, never the instruction — so the old
            // fixed SUMMARY_BUDGET cap is gone entirely; there is nothing
            // left for it to protect.
            let summary = snapshot.pause_summary.as_deref().unwrap_or("autopause");
            return Some(format!(
                "autopause pending — press 'a' to acknowledge ({summary})"
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
        // Materialize everything this function still needs off `row`
        // BEFORE the mutable `record_chrome_verb` call below — `row`
        // borrows `chrome`, which borrows `self.chrome`, and a `&mut self`
        // call cannot coexist with that borrow (R11's dispatch-proof
        // record must land before the refusal ladder, and the ladder and
        // the honest-target lookup after it both still read `row`).
        let verb = row.verb.clone();
        let eligible = row.eligible;
        let reason = row.reason.clone();
        let can_afford = row.can_afford;
        let afford_note_field = row.afford_note.clone();
        let candidate_target_ids = row.candidate_target_ids.clone();
        // R11 fix (verify-panel finding): record the verb BEFORE the
        // refusal ladder below — Textual's own keypress handler logs the
        // dispatch ahead of every eligibility/afford check, and
        // `chrome_verbs` must mean "the press reached verb dispatch" the
        // same way in both clients, not "the verb actually queued". The
        // host-log recording further down (`issue_verb`) stays as-is —
        // that one is reached-the-host proof, a different claim.
        self.record_chrome_verb(&verb);
        if !eligible {
            let reason = reason.unwrap_or_else(|| "ineligible".to_string());
            self.status = Some(format!("status: {verb} refused — {reason}"));
            return;
        }
        let afford_note = (!can_afford).then_some(afford_note_field).flatten();
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
            .filter(|id_part| candidate_target_ids.iter().any(|c| c == id_part));
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

    /// Re-pull the topology pane's payloads for its current (kind, focus)
    /// — pane entry, kind/mode change, and every committed tick (M4
    /// contract §3: without this the pane silently goes stale).
    fn refresh_topology(&mut self) {
        let focus = self.views.iter().find_map(|v| match v {
            View::Wiki(wiki) => wiki.current.clone(),
            View::Lobby(_) => None,
        });
        use crate::views::topology::TopologyMode;
        let (args, mode) = match self.chrome.as_mut() {
            Some(chrome) => (
                chrome.topology.args_json(focus.as_deref()),
                chrome.topology.mode(),
            ),
            None => return,
        };
        // Fetch only what the current mode consumes (verify-panel: the
        // double-fetch is ~6 ms on Wayne but ~100 ms at US scale on the
        // synchronous render path; the mode toggle already NeedsRefresh,
        // so the other payload hydrates lazily on switch).
        if mode == TopologyMode::Surface3d {
            let raw_field = self.recording().field_state_json();
            if let Some(chrome) = self.chrome.as_mut() {
                chrome.topology.ingest_field_state(&raw_field);
            }
        } else {
            let raw = self.recording().topology_json(&args);
            if let Some(chrome) = self.chrome.as_mut() {
                chrome.topology.ingest_topology(&raw);
            }
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
                                // M4: a committed tick invalidates the topology pane's payloads.
        if self
            .chrome
            .as_ref()
            .is_some_and(|chrome| chrome.pane == Pane::Topology)
        {
            self.refresh_topology();
        }
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
        // R13b fix: a tick is a predicate-input change (the re-opened
        // subject may differ, `chrome_verbs` may have grown) just like a
        // key press or a fresh bind.
        self.tutorial_poll_pending = true;
    }
}

/// The honest absence fence for the dashboard pane (contract §3) — one
/// CRIMSON line, `▌`-prefixed, naming the escape hatch back to the wiki.
const DASHBOARD_FENCE: &str =
    "▌ dashboard pane — not yet ported (M4/M5 land this surface); press '3' for the wiki";
/// Same as [`DASHBOARD_FENCE`], for the map pane.
const MAP_FENCE: &str =
    "▌ map pane — not yet ported (M4/M5 land this surface); press '3' for the wiki";

/// Render one line of `text` in CRIMSON into `area` — the not-yet-ported
/// pane fence (contract §3).
fn render_pane_absence(frame: &mut ratatui::Frame<'_>, area: Rect, text: &str) {
    let line = ratatui::text::Line::from(ratatui::text::Span::styled(
        text.to_string(),
        ratatui::style::Style::new().fg(crate::theme::CRIMSON),
    ));
    frame.render_widget(ratatui::widgets::Paragraph::new(line), area);
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
        // Wave 1 §4: without this name a headless BackTab test would be a
        // SILENT no-op (unknown names skip, by design) and pass vacuously.
        "backtab" => KeyCode::BackTab,
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
        // R13b note: the interactive transcript is discarded at quit
        // (`run`'s `"frames": []`) — draining every iteration keeps the
        // host-call log from growing unbounded across a long play session;
        // only headless replay needs the full, undrained history.
        app.drain_host_calls();
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
