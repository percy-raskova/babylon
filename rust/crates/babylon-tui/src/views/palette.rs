//! The command palette: fuzzy navigation over the known-subject set.
//!
//! Ports `babylon.tui.palette.EntityNavigatorProvider.search`'s ranking
//! semantics. That Python provider does not implement its own fuzzy
//! matching — it delegates to `Provider.matcher(query)`, which builds a
//! `textual.fuzzy.Matcher(query, case_sensitive=False)`, itself a thin
//! wrapper over `textual.fuzzy.FuzzySearch`. `fuzzy_score` below is a
//! faithful, from-source port of `FuzzySearch._match`/`FuzzySearch.score`
//! (`textual/fuzzy.py`, read from the vendored `.venv` at port time):
//!
//! * If (lowercased) `query` is a substring of (lowercased) `candidate`, the
//!   match is the contiguous run at its first occurrence, scored and then
//!   boosted ×2.0 (exact equality) or ×1.5 (proper substring) — Python's
//!   "quick exit when the query exists as a substring" path.
//! * Otherwise every query character must appear, in order, as a
//!   (possibly non-contiguous) subsequence of `candidate`; all valid
//!   subsequence position-combinations are scored and the best kept.
//! * The base score rewards more matched characters, extra credit for
//!   landing on a "word start" (the position just after a run of
//!   non-word characters — Python's `\w+` regex groups), and a
//!   `(1 + cohesion²)` multiplier that favors fewer, longer contiguous
//!   runs over many scattered single-character hits.
//!
//! One deliberate divergence: the Python `FuzzySearch.score` crashes
//! (`ValueError: not enough values to unpack`) when handed an empty-string
//! query — reachable in principle through `Provider.search("")`, but never
//! hit in practice because Textual's own command palette routes empty
//! input to `Provider.discover()` instead (`palette.py`'s own docstring:
//! "`discover()` is optional... empty-input suggestions"). [`PaletteView`]
//! mirrors that real dispatch rather than the underlying crash: an empty
//! query short-circuits to "every known subject, sorted" without ever
//! calling `fuzzy_score`.
//!
//! No verb commands here (design canon R4, `palette.py`'s own docstring):
//! the palette carries exactly one command shape, "open a known subject's
//! page" — [`AppEvent::OpenSubject`].

use std::collections::BTreeSet;

use ratatui::crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::{Block, Borders, Paragraph};
use ratatui::Frame;

use crate::views::msg::AppEvent;

/// The command palette view: fuzzy-filters the known-subject catalog as the
/// player types, and opens the highlighted match.
pub struct PaletteView {
    /// The full known-subject catalog, fixed at [`PaletteView::open`] time
    /// (the fuzzy filter always re-scores from this list, never from a
    /// previously-filtered subset — matching `EntityNavigatorProvider`,
    /// which re-scans `_known_entities(self.app)` on every keystroke).
    subjects: Vec<String>,
    /// The current query text, edited by [`PaletteView::handle_key`].
    pub query: String,
    /// Subjects passing the current query filter, ranked best match first
    /// (ties broken by subject id, ascending — deterministic; matches the
    /// Python provider's own iteration order, `sorted(_known_entities(...))`,
    /// which stable-sorts equal-score hits into id order).
    pub matches: Vec<String>,
    /// Index into [`PaletteView::matches`] of the highlighted row.
    pub selected: usize,
    /// `true` when the known-subjects payload failed to parse — rendered
    /// loudly, never conflated with "no matching subjects".
    pub parse_failed: bool,
}

impl PaletteView {
    /// Opens the palette over a `known_subjects_json` payload
    /// ([`crate::host::Host::known_subjects_json`]'s shape: a JSON array of
    /// subject-id strings). A malformed or absent payload opens with an
    /// honestly empty catalog rather than a fabricated one (Constitution
    /// III.11), mirroring `_known_entities`'s own absent-attribute fallback
    /// to `frozenset()`.
    pub fn open(known_subjects_json: &str) -> Self {
        let (subjects, parse_failed) =
            match serde_json::from_str::<Vec<String>>(known_subjects_json) {
                Ok(subjects) => (subjects, false),
                Err(_) => (Vec::new(), true),
            };
        let mut view = Self {
            subjects,
            query: String::new(),
            matches: Vec::new(),
            selected: 0,
            parse_failed,
        };
        view.refilter();
        view
    }

    /// Re-scores every known subject against the current query and rebuilds
    /// [`PaletteView::matches`], resetting the selection to the top hit.
    ///
    /// An empty query never calls `fuzzy_score` (see module docs): it
    /// lists every subject, sorted — the same shape as
    /// `EntityNavigatorProvider.discover()`.
    fn refilter(&mut self) {
        self.matches = if self.query.is_empty() {
            let mut all = self.subjects.clone();
            all.sort();
            all
        } else {
            let mut scored: Vec<(f64, &str)> = self
                .subjects
                .iter()
                .filter_map(|subject| {
                    let score = fuzzy_score(&self.query, subject);
                    (score > 0.0).then_some((score, subject.as_str()))
                })
                .collect();
            // Score descending; ties broken by subject id ascending — a
            // total order, so this sort's outcome never depends on the
            // input's original ordering (determinism, Constitution III.13).
            scored.sort_by(|a, b| {
                // `fuzzy_score` only ever combines finite arithmetic on
                // non-negative integers, so `partial_cmp` never returns
                // `None` in practice; the fallback keeps this comparator
                // total (and panic-free) even so.
                b.0.partial_cmp(&a.0)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| a.1.cmp(b.1))
            });
            scored
                .into_iter()
                .map(|(_, subject)| subject.to_string())
                .collect()
        };
        self.selected = 0;
    }

    /// Routes one key press.
    ///
    /// * A printable character or Backspace edits [`PaletteView::query`]
    ///   and re-filters.
    /// * Up/Down move [`PaletteView::selected`] within the current matches
    ///   (clamped, never wrapping).
    /// * Enter opens the highlighted match (`None` if there is nothing to
    ///   open — an honestly-empty match list).
    /// * Esc backs out of the palette.
    pub fn handle_key(&mut self, code: KeyCode) -> Option<AppEvent> {
        match code {
            KeyCode::Char(c) => {
                self.query.push(c);
                self.refilter();
                None
            }
            KeyCode::Backspace => {
                self.query.pop();
                self.refilter();
                None
            }
            KeyCode::Up => {
                self.selected = self.selected.saturating_sub(1);
                None
            }
            KeyCode::Down => {
                if self.selected + 1 < self.matches.len() {
                    self.selected += 1;
                }
                None
            }
            KeyCode::Enter => self
                .matches
                .get(self.selected)
                .cloned()
                .map(AppEvent::OpenSubject),
            KeyCode::Esc => Some(AppEvent::Back),
            _ => None,
        }
    }

    /// Renders the palette as a centered overlay box atop whatever `area`
    /// covers: a query line, then the ranked match list (the highlighted
    /// row reversed-video), or an honest-absence line when nothing matches.
    pub fn render(&self, frame: &mut Frame, area: Rect) {
        let overlay = centered_rect(60, 60, area);
        // Clear first: widgets only write where they have content, so the
        // view underneath would bleed through every unwritten overlay cell.
        frame.render_widget(ratatui::widgets::Clear, overlay);
        let block = Block::default().borders(Borders::ALL).title("Open subject");
        let inner = block.inner(overlay);
        frame.render_widget(block, overlay);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(1), Constraint::Min(1)])
            .split(inner);

        let query_line = Paragraph::new(Line::from(vec![
            Span::raw("> "),
            Span::raw(self.query.as_str()),
        ]));
        frame.render_widget(query_line, chunks[0]);

        if self.matches.is_empty() {
            // Honest absence (Constitution III.11): never a blank list —
            // and an unreadable catalog is an ERROR, not an empty result.
            let text = if self.parse_failed {
                "subject catalog UNREADABLE — malformed host data"
            } else {
                "no matching subjects"
            };
            let mut absence = Paragraph::new(text).alignment(Alignment::Left);
            if self.parse_failed {
                absence = absence.style(ratatui::style::Style::new().fg(crate::theme::CRIMSON));
            }
            frame.render_widget(absence, chunks[1]);
            return;
        }

        let lines: Vec<Line> = self
            .matches
            .iter()
            .enumerate()
            .map(|(index, subject)| {
                let style = if index == self.selected {
                    Style::default().add_modifier(Modifier::REVERSED)
                } else {
                    Style::default()
                };
                Line::from(Span::styled(subject.as_str(), style))
            })
            .collect();
        let list = Paragraph::new(Text::from(lines));
        frame.render_widget(list, chunks[1]);
    }
}

/// Carves a `percent_x`% × `percent_y`% box out of the center of `area`.
fn centered_rect(percent_x: u16, percent_y: u16, area: Rect) -> Rect {
    let vertical = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(area);
    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(vertical[1])[1]
}

/// Word-start positions in `chars`: the index just after any run boundary
/// into a run of "word" characters (alphanumeric or `_`).
///
/// Ports `FuzzySearch.get_first_letters`'s `re.finditer(r"\w+", candidate)`
/// start-offset set (over already-lowercased, already-char-indexed input;
/// Python string indices are code-point indices, matched here by indexing
/// `chars: &[char]` rather than raw byte offsets).
fn word_start_positions(chars: &[char]) -> BTreeSet<usize> {
    let mut starts = BTreeSet::new();
    let mut prev_is_word = false;
    for (index, ch) in chars.iter().enumerate() {
        let is_word = ch.is_alphanumeric() || *ch == '_';
        if is_word && !prev_is_word {
            starts.insert(index);
        }
        prev_is_word = is_word;
    }
    starts
}

/// Ports `FuzzySearch.score`: rewards more matched characters (plus a
/// bonus per position landing on a word start) and a cohesion multiplier
/// that favors fewer, longer contiguous runs of `positions`.
///
/// `positions` must be non-empty and strictly increasing (the only shape
/// `fuzzy_score` ever builds); an empty slice returns `0.0` defensively
/// (the Python original panics on this input instead — never reachable
/// from any call site here, since every caller below only invokes this
/// with at least one position).
fn score_positions(positions: &[usize], word_starts: &BTreeSet<usize>) -> f64 {
    let Some(&first) = positions.first() else {
        return 0.0;
    };
    let offset_count = positions.len();
    let word_start_hits = positions.iter().filter(|p| word_starts.contains(p)).count();
    let mut score = (offset_count + word_start_hits) as f64;

    let mut groups = 1usize;
    let mut last_offset = first;
    for &offset in &positions[1..] {
        if offset != last_offset + 1 {
            groups += 1;
        }
        last_offset = offset;
    }
    let normalized_groups = (offset_count as f64 - (groups as f64 - 1.0)) / offset_count as f64;
    score *= 1.0 + normalized_groups * normalized_groups;
    score
}

/// Finds the first index `>= start` in `chars` equal to `target`.
fn find_char_from(chars: &[char], target: char, start: usize) -> Option<usize> {
    chars[start.min(chars.len())..]
        .iter()
        .position(|&c| c == target)
        .map(|offset| offset + start)
}

/// Finds the first (leftmost) index where `needle` occurs as a contiguous
/// run within `haystack`, or `None`.
fn find_subsequence_run(haystack: &[char], needle: &[char]) -> Option<usize> {
    if needle.is_empty() {
        return Some(0);
    }
    if needle.len() > haystack.len() {
        return None;
    }
    (0..=(haystack.len() - needle.len()))
        .find(|&start| haystack[start..start + needle.len()] == *needle)
}

/// Recursively enumerates every strictly-increasing offset combination
/// drawing one position per query character from `letter_positions` (in
/// order), scoring each complete combination and keeping the best.
///
/// Ports `FuzzySearch._match`'s nested `get_offsets` closure. Recursion
/// depth is bounded by `query_length` (the number of query characters,
/// fixed and small for palette queries) — a statically bounded descent,
/// never unbounded.
fn best_combination_score(
    letter_positions: &[Vec<usize>],
    positions_index: usize,
    current: &mut Vec<usize>,
    query_length: usize,
    word_starts: &BTreeSet<usize>,
    best: &mut f64,
) {
    for &offset in &letter_positions[positions_index] {
        if current.last().is_some_and(|&last| offset <= last) {
            continue;
        }
        current.push(offset);
        if current.len() == query_length {
            let candidate_score = score_positions(current, word_starts);
            if candidate_score > *best {
                *best = candidate_score;
            }
        } else {
            best_combination_score(
                letter_positions,
                positions_index + 1,
                current,
                query_length,
                word_starts,
                best,
            );
        }
        current.pop();
    }
}

/// Scores `candidate` against `query`, case-insensitively — a from-source
/// port of `textual.fuzzy.FuzzySearch.match(query, candidate)[0]` (the
/// score half of its `(score, offsets)` pair; see module docs for the
/// algorithm and its one deliberate divergence).
///
/// Returns `0.0` for no match (including the never-hit-in-practice empty
/// query, guarded here rather than replicating the Python crash — see
/// module docs) and a positive score otherwise; higher is a tighter match.
pub(crate) fn fuzzy_score(query: &str, candidate: &str) -> f64 {
    if query.is_empty() {
        return 0.0;
    }
    let query_chars: Vec<char> = query.to_lowercase().chars().collect();
    let candidate_chars: Vec<char> = candidate.to_lowercase().chars().collect();

    if let Some(start) = find_subsequence_run(&candidate_chars, &query_chars) {
        let offsets: Vec<usize> = (start..start + query_chars.len()).collect();
        let word_starts = word_start_positions(&candidate_chars);
        let base = score_positions(&offsets, &word_starts);
        return base
            * if candidate_chars == query_chars {
                2.0
            } else {
                1.5
            };
    }

    let candidate_len = candidate_chars.len();
    let mut letter_positions: Vec<Vec<usize>> = Vec::with_capacity(query_chars.len());
    let mut window_start = 0usize;
    for (query_offset, &letter) in query_chars.iter().enumerate() {
        // Signed: Python's `len(candidate) - offset` may go negative when
        // the query outruns the candidate, which only tightens (never
        // panics) the `index >= last_index` break check below.
        let last_index = candidate_len as i64 - query_offset as i64;
        let mut positions = Vec::new();
        let mut index = window_start;
        while let Some(location) = find_char_from(&candidate_chars, letter, index) {
            positions.push(location);
            index = location + 1;
            if index as i64 >= last_index {
                break;
            }
        }
        if positions.is_empty() {
            return 0.0;
        }
        window_start = positions[0] + 1;
        letter_positions.push(positions);
    }

    let word_starts = word_start_positions(&candidate_chars);
    let mut best = 0.0f64;
    let mut current = Vec::with_capacity(query_chars.len());
    best_combination_score(
        &letter_positions,
        0,
        &mut current,
        query_chars.len(),
        &word_starts,
        &mut best,
    );
    best
}

#[cfg(test)]
mod tests {
    use super::*;

    // Exact float values captured from the vendored Textual runtime itself:
    //
    //     .venv/bin/python3 -c "
    //     from textual.fuzzy import FuzzySearch
    //     fs = FuzzySearch()
    //     print(fs.match('county/26163', 'county/26163'))
    //     print(fs.match('county', 'county/26163'))
    //     print(fs.match('c26163', 'county/26163'))
    //     print(fs.match('tenants', 'org/tenants-un'))
    //     print(fs.match('tenants', 'org/uaw-9999'))
    //     "
    //
    // pinning `fuzzy_score` to the real algorithm's own numbers, not just
    // its ranking order.

    #[test]
    fn exact_match_scores_56() {
        assert_eq!(fuzzy_score("county/26163", "county/26163"), 56.0);
    }

    #[test]
    fn tight_prefix_substring_scores_21() {
        assert_eq!(fuzzy_score("county", "county/26163"), 21.0);
    }

    #[test]
    fn scattered_subsequence_scores_13_5556() {
        let score = fuzzy_score("c26163", "county/26163");
        assert!((score - 13.555_555_555_555_557).abs() < 1e-9, "got {score}");
    }

    #[test]
    fn substring_mid_word_scores_24() {
        assert_eq!(fuzzy_score("tenants", "org/tenants-un"), 24.0);
    }

    #[test]
    fn no_common_subsequence_scores_zero() {
        assert_eq!(fuzzy_score("tenants", "org/uaw-9999"), 0.0);
    }

    #[test]
    fn case_insensitive_matches_the_lowercase_score() {
        assert_eq!(fuzzy_score("COUNTY", "county/26163"), 21.0);
    }

    #[test]
    fn empty_query_never_panics_and_scores_zero() {
        assert_eq!(fuzzy_score("", "county/26163"), 0.0);
    }

    #[test]
    fn query_longer_than_candidate_scores_zero() {
        assert_eq!(fuzzy_score("countycountycounty", "county"), 0.0);
    }
}
