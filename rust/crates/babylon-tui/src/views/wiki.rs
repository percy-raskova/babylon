//! The Archive reading view: renders one wiki page and its link spans, with
//! vim-style jumplist navigation (`Ctrl-O`/`Ctrl-I`, `[`/`]`; plan Task 15),
//! a keyboard link cursor (`n`/`p` — keyboard peek is first-class, mouse
//! hover is never load-bearing, per the S7 canon `peek.rs` quotes), and a
//! "What links here" backlinks footer (the Task 17 read path's consumer —
//! ADR109: a seam without a caller is an unclosed motion).
//!
//! Mirrors the jumplist semantics of `babylon.tui.nav.JumplistState` (visit
//! truncates forward history; `back`/`forward` are idempotent at the edges)
//! but is not a line-for-line port: [`WikiView`] stores plain subject
//! strings with no Pydantic model and no persistence seam — M1 is
//! read-only, and `NavPersistence` stays a Python-side concern for M2.
//!
//! **Wrapping**: pages wrap to the pane width with a span-preserving greedy
//! word wrap done HERE, not by `Paragraph::wrap` — the layout registry and
//! the link cursor need to know exactly which display cells each wikilink
//! occupies, and ratatui's own wrapping discards that mapping. babylon-md
//! folds Markdown soft breaks into long logical lines, so without this every
//! real vault paragraph would clip at the pane edge unreachably (the M1
//! verify panel's finding). Continuation rows do not repeat block prefixes
//! (a wrapped blockquote row loses its `▌ ` gutter) — accepted for M1.

use std::collections::BTreeSet;

use ratatui::crossterm::event::{KeyCode, KeyModifiers};
use ratatui::layout::Rect;
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;
use unicode_width::UnicodeWidthStr;

use crate::host::Host;
use crate::layout_registry::{LayoutRegistry, WidgetId};
use crate::router::BabylonTarget;
use crate::theme::{DIM, GOLD};
use crate::views::msg::AppEvent;
use crate::wiki_render::render_page;

/// Lines scrolled per `PageUp`/`PageDown` — a display constant for this
/// view, not a `GameDefines` coefficient (no gameplay tuning involved).
const PAGE_SCROLL: u16 = 10;

/// One navigable link in the laid-out page: a target plus the display-cell
/// segments its label occupies (row, col start, col end — cols relative to
/// the pane's inner area, rows relative to the unscrolled layout).
#[derive(Debug, Clone, PartialEq, Eq)]
struct LinkHit {
    target: String,
    segments: Vec<(usize, u16, u16)>,
}

/// The wrapped, hit-mapped layout of the current page at one pane width.
#[derive(Debug, Default)]
struct PageLayout {
    /// Width the layout was computed for (`0` = layout absent/stale).
    width: u16,
    /// Display rows (already wrapped; index = unscrolled row).
    rows: Vec<Line<'static>>,
    /// Navigable links in document order (content links, then backlinks).
    hits: Vec<LinkHit>,
}

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
    /// Vertical scroll offset (rows), clamped to the content in `render`.
    scroll: u16,
    /// The raw Markdown for `current`, cached on `open` so `render` never
    /// touches the host (design §4 — the seam is crossed once, on demand).
    page_markdown: String,
    /// Subjects linking TO `current` (the Task 17 backlink read path),
    /// fetched on `open`, rendered as the "What links here" footer.
    backlinks: Vec<String>,
    /// The wrapped layout, rebuilt lazily when the pane width changes.
    layout: PageLayout,
    /// Keyboard link cursor: index into `layout.hits` (`None` = no focus).
    cursor: Option<usize>,
    /// Inner pane height seen at the last render (scroll clamp input).
    last_height: u16,
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
    /// the honest-absence page when the host has none), fetch its
    /// backlinks, and record the visit in the jumplist.
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
        let raw_backlinks = host.backlinks_json(&subject);
        self.backlinks = serde_json::from_str(&raw_backlinks).unwrap_or_default();
        self.push_jump(&subject);
        self.page_markdown = page;
        self.scroll = 0;
        self.cursor = None;
        self.layout = PageLayout::default();
    }

    /// Show a synthetic page (the shell's loud-failure channel) without
    /// touching the host — used for campaign-load failures, which must
    /// never render as an empty world (Constitution III.11).
    pub fn open_page(&mut self, subject: &str, markdown: String) {
        self.backlinks = Vec::new();
        self.push_jump(subject);
        self.page_markdown = markdown;
        self.scroll = 0;
        self.cursor = None;
        self.layout = PageLayout::default();
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

    /// The link target the keyboard cursor currently focuses, if any —
    /// the app shell feeds this to the peek overlay (keyboard peek is
    /// first-class; mouse hover is never load-bearing).
    #[must_use]
    pub fn focused_target(&self) -> Option<&str> {
        self.cursor
            .and_then(|idx| self.layout.hits.get(idx))
            .map(|hit| hit.target.as_str())
    }

    /// Move the link cursor by `delta` (wrapping), scrolling the focused
    /// link into view.
    fn move_cursor(&mut self, delta: isize) {
        let count = self.layout.hits.len();
        if count == 0 {
            return;
        }
        let next = match self.cursor {
            None if delta >= 0 => 0,
            None => count - 1,
            Some(idx) => (idx as isize + delta).rem_euclid(count as isize) as usize,
        };
        self.cursor = Some(next);
        if let Some(first_row) = self.layout.hits[next].segments.first().map(|s| s.0) {
            let row = first_row as u16;
            let height = self.last_height.max(1);
            if row < self.scroll {
                self.scroll = row;
            } else if row >= self.scroll + height {
                self.scroll = row + 1 - height;
            }
        }
    }

    /// The largest useful scroll offset for the current layout (the last
    /// content row rests on the bottom pane row; 0 while content fits).
    fn max_scroll(&self) -> u16 {
        let rows = self.layout.rows.len() as u16;
        rows.saturating_sub(self.last_height.max(1))
    }

    /// Handle one key event, returning the app event (if any) to route.
    ///
    /// `[`/`Ctrl-O` walk back; `]`/`Ctrl-I` walk forward — both emit
    /// `AppEvent::OpenSubject` for the shell to re-open. `n`/`p` move the
    /// keyboard link cursor (next/previous, wrapping) and `Enter` opens the
    /// focused link. `Up`/`Down` scroll by one row, `PageUp`/`PageDown` by
    /// `PAGE_SCROLL`, clamped to the content. `q`/`Esc` emit
    /// `AppEvent::Back`.
    ///
    /// Takes `modifiers` in addition to `code` — a deliberate deviation
    /// from the crate's other views (`LobbyView::handle_key` takes only
    /// `code`): `Ctrl-O`/`Ctrl-I` are not representable in `KeyCode` alone,
    /// only via `KeyModifiers::CONTROL`.
    pub fn handle_key(&mut self, code: KeyCode, modifiers: KeyModifiers) -> Option<AppEvent> {
        let ctrl = modifiers.contains(KeyModifiers::CONTROL);
        match code {
            KeyCode::Char('[') => self.back().map(AppEvent::OpenSubject),
            KeyCode::Char(']') => self.forward().map(AppEvent::OpenSubject),
            KeyCode::Char('o' | 'O') if ctrl => self.back().map(AppEvent::OpenSubject),
            KeyCode::Char('i' | 'I') if ctrl => self.forward().map(AppEvent::OpenSubject),
            KeyCode::Char('n') => {
                self.move_cursor(1);
                None
            }
            KeyCode::Char('p') => {
                self.move_cursor(-1);
                None
            }
            KeyCode::Enter => self
                .focused_target()
                .map(|target| AppEvent::OpenSubject(target.to_string())),
            KeyCode::Up => {
                self.scroll = self.scroll.saturating_sub(1);
                None
            }
            KeyCode::Down => {
                self.scroll = self.scroll.saturating_add(1).min(self.max_scroll());
                None
            }
            KeyCode::PageUp => {
                self.scroll = self.scroll.saturating_sub(PAGE_SCROLL);
                None
            }
            KeyCode::PageDown => {
                self.scroll = self
                    .scroll
                    .saturating_add(PAGE_SCROLL)
                    .min(self.max_scroll());
                None
            }
            KeyCode::Char('q') | KeyCode::Esc => Some(AppEvent::Back),
            _ => None,
        }
    }

    /// Rebuild the wrapped layout when the pane width changed.
    fn ensure_layout(&mut self, width: u16, known: &BTreeSet<String>) {
        if self.layout.width == width && width != 0 {
            return;
        }
        self.layout = build_layout(&self.page_markdown, &self.backlinks, width, known);
        self.cursor = self.cursor.filter(|idx| *idx < self.layout.hits.len());
    }

    /// Render the cached page into `area` of `frame`.
    ///
    /// Pipeline: `page_markdown` → [`render_page`] → span-preserving word
    /// wrap (+ the backlinks footer) → a scrolled, bordered `Paragraph`;
    /// every visible link segment registers into `registry` (entity = the
    /// link target) and the keyboard-focused link renders reversed.
    pub fn render(
        &mut self,
        frame: &mut Frame<'_>,
        area: Rect,
        registry: &mut LayoutRegistry,
        known: &BTreeSet<String>,
    ) {
        let title = self.current.as_deref().unwrap_or("Wiki").to_string();
        let block = Block::bordered().title(title);
        let inner = block.inner(area);
        self.last_height = inner.height;
        self.ensure_layout(inner.width, known);
        self.scroll = self.scroll.min(self.max_scroll());

        let focused: Vec<(usize, u16, u16)> = self
            .cursor
            .and_then(|idx| self.layout.hits.get(idx))
            .map(|hit| hit.segments.clone())
            .unwrap_or_default();
        let mut rows = self.layout.rows.clone();
        for (row, col_start, col_end) in &focused {
            if let Some(line) = rows.get_mut(*row) {
                *line = highlight_segment(line, *col_start, *col_end);
            }
        }

        let paragraph = Paragraph::new(rows).block(block).scroll((self.scroll, 0));
        frame.render_widget(paragraph, area);

        for (idx, hit) in self.layout.hits.iter().enumerate() {
            for (row, col_start, col_end) in &hit.segments {
                let screen_row = *row as i64 - i64::from(self.scroll);
                if screen_row < 0 || screen_row as u16 >= inner.height {
                    continue; // scrolled out of view
                }
                let col_start = (*col_start).min(inner.width);
                let col_end = (*col_end).min(inner.width);
                if col_end <= col_start {
                    continue;
                }
                let rect = Rect {
                    x: inner.x + col_start,
                    y: inner.y + screen_row as u16,
                    width: col_end - col_start,
                    height: 1,
                };
                registry.register(WidgetId(idx as u32), rect, Some(hit.target.clone()));
            }
        }
    }
}

/// One wrap-unit: a word or run of spaces from one source span, with its
/// provenance (source line + span index) for link-range mapping.
#[derive(Debug, Clone)]
struct Chunk {
    text: String,
    style: Style,
    orig_line: usize,
    orig_span: usize,
}

impl Chunk {
    fn width(&self) -> u16 {
        self.text.as_str().width() as u16
    }
}

/// Re-style `[col_start, col_end)` of `line` with `REVERSED` (the keyboard
/// link-cursor highlight), splitting spans at the boundaries.
fn highlight_segment(line: &Line<'static>, col_start: u16, col_end: u16) -> Line<'static> {
    let mut out: Vec<Span<'static>> = Vec::new();
    let mut col: u16 = 0;
    for span in &line.spans {
        let w = span.content.as_ref().width() as u16;
        let (start, end) = (col, col + w);
        if end <= col_start || start >= col_end {
            out.push(span.clone());
        } else {
            // Split by display cells; labels are narrow so a char walk is fine.
            let mut acc_plain = String::new();
            let mut acc_hot = String::new();
            let mut acc_tail = String::new();
            let mut c = start;
            for ch in span.content.chars() {
                let cw = ch.to_string().as_str().width() as u16;
                if c + cw <= col_start {
                    acc_plain.push(ch);
                } else if c < col_end {
                    acc_hot.push(ch);
                } else {
                    acc_tail.push(ch);
                }
                c += cw;
            }
            if !acc_plain.is_empty() {
                out.push(Span::styled(acc_plain, span.style));
            }
            if !acc_hot.is_empty() {
                out.push(Span::styled(
                    acc_hot,
                    span.style.add_modifier(Modifier::REVERSED),
                ));
            }
            if !acc_tail.is_empty() {
                out.push(Span::styled(acc_tail, span.style));
            }
        }
        col += w;
    }
    let mut new_line = Line::from(out);
    new_line.style = line.style;
    new_line.alignment = line.alignment;
    new_line
}

/// Build the wrapped, hit-mapped layout: render the page, word-wrap it to
/// `width` preserving span provenance, map each wikilink's span range to
/// display segments, then append the "What links here" footer (each
/// backlink itself a navigable hit).
fn build_layout(
    markdown: &str,
    backlinks: &[String],
    width: u16,
    known: &BTreeSet<String>,
) -> PageLayout {
    let width = width.max(1);
    let (text, links) = render_page(markdown, width, known);

    let mut rows: Vec<Line<'static>> = Vec::new();
    // Per placed row: the chunks with provenance, for link mapping.
    let mut placed: Vec<Vec<(Chunk, u16, u16)>> = Vec::new();

    for (orig_line, line) in text.lines.iter().enumerate() {
        let chunks = chop_line(line, orig_line);
        let wrapped = wrap_chunks(&chunks, width);
        if wrapped.is_empty() {
            rows.push(Line::default().style(line.style));
            placed.push(Vec::new());
            continue;
        }
        for row_chunks in wrapped {
            let mut spans: Vec<Span<'static>> = Vec::new();
            let mut with_cols: Vec<(Chunk, u16, u16)> = Vec::new();
            let mut col: u16 = 0;
            for chunk in row_chunks {
                let w = chunk.width();
                spans.push(Span::styled(chunk.text.clone(), chunk.style));
                with_cols.push((chunk, col, col + w));
                col += w;
            }
            let mut new_line = Line::from(spans);
            new_line.style = line.style;
            rows.push(new_line);
            placed.push(with_cols);
        }
    }

    // Map each wikilink's (line, span) range onto placed display segments.
    let mut hits: Vec<LinkHit> = Vec::new();
    for link in &links {
        let Some(pos) = &link.position else { continue };
        let in_range = |chunk: &Chunk| {
            let at = (chunk.orig_line, chunk.orig_span);
            at >= (pos.start_line, pos.start_span)
                && (chunk.orig_line < pos.end_line
                    || (chunk.orig_line == pos.end_line && chunk.orig_span < pos.end_span))
        };
        let mut segments: Vec<(usize, u16, u16)> = Vec::new();
        for (row, row_chunks) in placed.iter().enumerate() {
            let mut run: Option<(u16, u16)> = None;
            for (chunk, start, end) in row_chunks {
                if in_range(chunk) && !chunk.text.trim().is_empty() {
                    run = Some(match run {
                        None => (*start, *end),
                        Some((s, _)) => (s, *end),
                    });
                } else if let Some(done) = run.take() {
                    segments.push((row, done.0, done.1));
                }
            }
            if let Some(done) = run.take() {
                segments.push((row, done.0, done.1));
            }
        }
        if !segments.is_empty() {
            hits.push(LinkHit {
                target: link.target.clone(),
                segments,
            });
        }
    }

    // The backlinks footer (ADR109: the Task 17 seam's consumer).
    if !backlinks.is_empty() {
        rows.push(Line::default());
        rows.push(Line::from(Span::styled(
            "── What links here ──",
            Style::new().fg(DIM),
        )));
        for backlink in backlinks {
            let row = rows.len();
            let marker = "· ";
            let col_start = marker.width() as u16;
            let col_end = col_start + backlink.as_str().width() as u16;
            rows.push(Line::from(vec![
                Span::styled(marker, Style::new().fg(DIM)),
                Span::styled(backlink.clone(), Style::new().fg(GOLD)),
            ]));
            hits.push(LinkHit {
                target: backlink.clone(),
                segments: vec![(row, col_start.min(width), col_end.min(width))],
            });
        }
    }

    PageLayout { width, rows, hits }
}

/// Split one source line's spans into word/space chunks with provenance.
fn chop_line(line: &Line<'_>, orig_line: usize) -> Vec<Chunk> {
    let mut chunks = Vec::new();
    for (orig_span, span) in line.spans.iter().enumerate() {
        let content = span.content.as_ref();
        let mut current = String::new();
        let mut current_is_space: Option<bool> = None;
        for ch in content.chars() {
            let is_space = ch == ' ';
            if current_is_space != Some(is_space) && !current.is_empty() {
                chunks.push(Chunk {
                    text: std::mem::take(&mut current),
                    style: span.style,
                    orig_line,
                    orig_span,
                });
            }
            current_is_space = Some(is_space);
            current.push(ch);
        }
        if !current.is_empty() {
            chunks.push(Chunk {
                text: current,
                style: span.style,
                orig_line,
                orig_span,
            });
        }
    }
    chunks
}

/// Greedy word wrap of a chunk list to `width` display cells. A chunk wider
/// than the whole pane splits at cell boundaries; leading spaces on a
/// continuation row are dropped (standard greedy-wrap convention).
fn wrap_chunks(chunks: &[Chunk], width: u16) -> Vec<Vec<Chunk>> {
    let mut out: Vec<Vec<Chunk>> = Vec::new();
    let mut row: Vec<Chunk> = Vec::new();
    let mut col: u16 = 0;
    for chunk in chunks {
        let mut chunk = chunk.clone();
        loop {
            let w = chunk.width();
            if col + w <= width {
                col += w;
                row.push(chunk);
                break;
            }
            let is_space = chunk.text.starts_with(' ');
            if !is_space && w <= width {
                // Word fits on a fresh row: wrap first.
                out.push(std::mem::take(&mut row));
                col = 0;
                continue;
            }
            if is_space {
                // Spaces never carry onto a continuation row.
                let keep = (width - col) as usize;
                let kept: String = chunk.text.chars().take(keep).collect();
                if !kept.is_empty() {
                    row.push(Chunk {
                        text: kept,
                        ..chunk.clone()
                    });
                }
                out.push(std::mem::take(&mut row));
                col = 0;
                break;
            }
            // A single word wider than the pane: hard-split at the edge.
            let available = (width - col) as usize;
            let mut head = String::new();
            let mut used = 0usize;
            let mut rest = String::new();
            for ch in chunk.text.chars() {
                let cw = ch.to_string().as_str().width();
                if rest.is_empty() && used + cw <= available && cw > 0 {
                    head.push(ch);
                    used += cw;
                } else {
                    rest.push(ch);
                }
            }
            if head.is_empty() {
                // No room on this row at all: wrap and retry.
                out.push(std::mem::take(&mut row));
                col = 0;
                continue;
            }
            row.push(Chunk {
                text: head,
                ..chunk.clone()
            });
            out.push(std::mem::take(&mut row));
            col = 0;
            chunk = Chunk {
                text: rest,
                ..chunk
            };
            if chunk.text.is_empty() {
                break;
            }
        }
    }
    if !row.is_empty() {
        out.push(row);
    }
    out
}
