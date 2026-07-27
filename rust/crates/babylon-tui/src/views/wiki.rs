//! The Archive reading view: renders one wiki page and its link spans, with
//! vim-style jumplist navigation (`Ctrl-O`/`Ctrl-I`, `[`/`]`; plan Task 15).
//!
//! Mirrors the jumplist semantics of `babylon.tui.nav.JumplistState` (visit
//! truncates forward history; `back`/`forward` are idempotent at the edges)
//! but is not a line-for-line port: [`WikiView`] stores plain subject
//! strings with no Pydantic model and no persistence seam — M1 is
//! read-only, and `NavPersistence` stays a Python-side concern for M2.

use std::collections::BTreeSet;

use ratatui::crossterm::event::{KeyCode, KeyModifiers};
use ratatui::layout::Rect;
use ratatui::text::Line;
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;

use crate::host::Host;
use crate::layout_registry::{LayoutRegistry, WidgetId};
use crate::router::BabylonTarget;
use crate::views::msg::AppEvent;
use crate::wiki_render::{render_page, LinkPosition};

/// Lines scrolled per `PageUp`/`PageDown` — a display constant for this
/// view, not a `GameDefines` coefficient (no gameplay tuning involved).
const PAGE_SCROLL: u16 = 10;

/// The Archive reading view over one open wiki page.
///
/// `jumplist`/`jumplist_idx` form a vim-style back-stack: `jumplist_idx`
/// indexes into `jumplist` and is only meaningful while `jumplist` is
/// non-empty (an empty jumplist means no page has ever been opened).
#[derive(Debug, Default)]
pub struct WikiView {
    /// The subject the view is positioned at.
    ///
    /// Stays in sync with `jumplist[jumplist_idx]` through `open`, `back`
    /// and `forward` alike — but note `back`/`forward` move the cursor
    /// WITHOUT re-fetching `page_markdown` (see their docs): `current` can
    /// therefore briefly name a subject the rendered page doesn't match
    /// until the app shell re-opens it.
    pub current: Option<String>,
    /// Visited subjects, oldest first — the full back-stack, not merely a
    /// display trail.
    pub jumplist: Vec<String>,
    /// Index of `current` within `jumplist`; meaningless while `jumplist`
    /// is empty.
    pub jumplist_idx: usize,
    /// Vertical scroll offset (rows), saturating at both ends.
    scroll: u16,
    /// The raw Markdown for `current`, cached on `open` so `render` never
    /// touches the host (design §4 — the seam is crossed once, on demand).
    page_markdown: String,
}

impl WikiView {
    /// A fresh view with no page open.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Resolve `target` to the subject id the host indexes pages under.
    ///
    /// `Entity(id)` and `Redlink(id)` both resolve to the bare id;
    /// `Kind{kind, id}` resolves to `"<kind>/<id>"` (mirrors
    /// `nav.subject_for`'s explicit-kind branch). Unlike
    /// `nav.subject_for`, a redlink resolves here rather than raising —
    /// rendering the honest-absence page for exactly that case is this
    /// view's job, not an error path.
    fn resolve_subject(target: &BabylonTarget) -> String {
        match target {
            BabylonTarget::Entity(id) | BabylonTarget::Redlink(id) => id.clone(),
            BabylonTarget::Kind { kind, id } => format!("{kind}/{id}"),
        }
    }

    /// The deterministic honest-absence page for a subject with no
    /// recorded page (Constitution III.11 — never fabricate content).
    fn honest_absence_page(subject: &str) -> String {
        format!("# {subject}\n\nNo page recorded for this subject.")
    }

    /// Navigate to `target`: resolve its subject, load the page (or render
    /// the honest-absence page when the host has none), and record the
    /// visit in the jumplist.
    ///
    /// Truncates any forward history when opening from mid-jumplist (the
    /// browser-navigation convention, `JumplistState.visit`) and is
    /// idempotent for the subject already current: re-opening the current
    /// page leaves the jumplist untouched but still refreshes
    /// `page_markdown` (the mechanism `back`/`forward` rely on the shell
    /// to invoke via `AppEvent::OpenSubject`).
    pub fn open(&mut self, target: &BabylonTarget, host: &dyn Host) {
        let subject = Self::resolve_subject(target);
        let raw = host.read_page_json(&subject);
        let page = match serde_json::from_str::<Option<String>>(&raw) {
            Ok(Some(markdown)) => markdown,
            Ok(None) | Err(_) => Self::honest_absence_page(&subject),
        };
        self.push_jump(&subject);
        self.page_markdown = page;
        self.scroll = 0;
    }

    /// Record a visit in the jumplist (the `JumplistState.visit` port).
    fn push_jump(&mut self, subject: &str) {
        if self.current.as_deref() == Some(subject) {
            return;
        }
        let kept_len = if self.jumplist.is_empty() {
            0
        } else {
            self.jumplist_idx + 1
        };
        self.jumplist.truncate(kept_len);
        self.jumplist.push(subject.to_string());
        self.jumplist_idx = self.jumplist.len() - 1;
        self.current = Some(subject.to_string());
    }

    /// Walk one step back (`Ctrl-O`/`[`); idempotent at the oldest entry.
    ///
    /// Returns the subject now positioned at (for the caller to re-open),
    /// or `None` when already at the oldest entry (or the jumplist is
    /// empty). Does not itself reload `page_markdown` — see the struct
    /// docs on `current`.
    pub fn back(&mut self) -> Option<String> {
        if self.jumplist.is_empty() || self.jumplist_idx == 0 {
            return None;
        }
        self.jumplist_idx -= 1;
        let subject = self.jumplist[self.jumplist_idx].clone();
        self.current = Some(subject.clone());
        Some(subject)
    }

    /// Walk one step forward (`Ctrl-I`/`]`); idempotent at the newest entry.
    ///
    /// See [`Self::back`] for the re-open contract and the return shape.
    pub fn forward(&mut self) -> Option<String> {
        if self.jumplist.is_empty() || self.jumplist_idx + 1 >= self.jumplist.len() {
            return None;
        }
        self.jumplist_idx += 1;
        let subject = self.jumplist[self.jumplist_idx].clone();
        self.current = Some(subject.clone());
        Some(subject)
    }

    /// Handle one key event, returning the app event (if any) to route.
    ///
    /// `[` and `Ctrl-O` walk back; `]` and `Ctrl-I` walk forward — both
    /// emit `AppEvent::OpenSubject` for the shell to re-open. `Up`/`Down`
    /// adjust scroll by one row, `PageUp`/`PageDown` by `PAGE_SCROLL`
    /// rows, both saturating. `q`/`Esc` emit `AppEvent::Back`.
    ///
    /// Takes `modifiers` in addition to `code` — a deliberate deviation
    /// from the crate's other views (`LobbyView::handle_key` takes only
    /// `code`): `Ctrl-O`/`Ctrl-I` are not representable in `KeyCode` alone,
    /// only via `KeyModifiers::CONTROL`. See the task report for the full
    /// rationale.
    pub fn handle_key(&mut self, code: KeyCode, modifiers: KeyModifiers) -> Option<AppEvent> {
        let ctrl = modifiers.contains(KeyModifiers::CONTROL);
        match code {
            KeyCode::Char('[') => self.back().map(AppEvent::OpenSubject),
            KeyCode::Char(']') => self.forward().map(AppEvent::OpenSubject),
            KeyCode::Char('o' | 'O') if ctrl => self.back().map(AppEvent::OpenSubject),
            KeyCode::Char('i' | 'I') if ctrl => self.forward().map(AppEvent::OpenSubject),
            KeyCode::Up => {
                self.scroll = self.scroll.saturating_sub(1);
                None
            }
            KeyCode::Down => {
                self.scroll = self.scroll.saturating_add(1);
                None
            }
            KeyCode::PageUp => {
                self.scroll = self.scroll.saturating_sub(PAGE_SCROLL);
                None
            }
            KeyCode::PageDown => {
                self.scroll = self.scroll.saturating_add(PAGE_SCROLL);
                None
            }
            KeyCode::Char('q') | KeyCode::Esc => Some(AppEvent::Back),
            _ => None,
        }
    }

    /// Render the cached page into `area` of `frame`.
    ///
    /// Pipeline: `page_markdown` → [`render_page`] → a scrolled, bordered
    /// `Paragraph`, then every returned `LinkSpan`'s on-screen rect is
    /// registered into `registry` (entity = the link target), accounting
    /// for the current scroll offset and the block's border inset. A link
    /// scrolled entirely out of the visible area is not registered.
    pub fn render(
        &self,
        frame: &mut Frame<'_>,
        area: Rect,
        registry: &mut LayoutRegistry,
        known: &BTreeSet<String>,
    ) {
        let title = self.current.as_deref().unwrap_or("Wiki");
        let block = Block::bordered().title(title);
        let inner = block.inner(area);
        let (text, links) = render_page(&self.page_markdown, inner.width, known);
        let paragraph = Paragraph::new(text.clone())
            .block(block)
            .scroll((self.scroll, 0));
        frame.render_widget(paragraph, area);

        for (idx, link) in links.iter().enumerate() {
            let Some(pos) = &link.position else {
                continue;
            };
            for line_idx in pos.start_line..=pos.end_line {
                let Some(line) = text.lines.get(line_idx) else {
                    continue;
                };
                let Some((col_start, col_end)) = column_range(line, pos, line_idx) else {
                    continue;
                };
                let screen_row = line_idx as i64 - i64::from(self.scroll);
                if screen_row < 0 || screen_row as u16 >= inner.height {
                    continue; // scrolled out of view
                }
                let col_start = col_start.min(inner.width as usize) as u16;
                let col_end = col_end.min(inner.width as usize) as u16;
                if col_end <= col_start {
                    continue;
                }
                let rect = Rect {
                    x: inner.x + col_start,
                    y: inner.y + screen_row as u16,
                    width: col_end - col_start,
                    height: 1,
                };
                registry.register(WidgetId(idx as u32), rect, Some(link.target.clone()));
            }
        }
    }
}

/// The `[start, end)` column range `pos` covers on `line_idx` of `line`
/// (display-cell widths, not byte offsets — wide glyphs count correctly).
///
/// `start_span` is inclusive, `end_span` exclusive (the `LinkPosition`
/// contract); a line strictly between `start_line` and `end_line` is
/// covered in full — the case of a link label wrapped across more than
/// two display lines.
fn column_range(line: &Line<'_>, pos: &LinkPosition, line_idx: usize) -> Option<(usize, usize)> {
    let spans = &line.spans;
    let width_before = |upto: usize| -> usize {
        spans
            .iter()
            .take(upto)
            .map(ratatui::text::Span::width)
            .sum()
    };
    let line_width: usize = spans.iter().map(ratatui::text::Span::width).sum();

    let start = if line_idx == pos.start_line {
        width_before(pos.start_span)
    } else {
        0
    };
    let end = if line_idx == pos.end_line {
        width_before(pos.end_span)
    } else {
        line_width
    };
    Some((start, end))
}
