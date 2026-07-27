//! Markdown link rendering.
//!
//! Links render as `label (destination)`. The link style applies to the label and destination while
//! nested inline formatting remains on the label.
//!
//! BABYLON PATCH 2 (fork): link metadata is retained through a side-channel
//! sink instead of being discarded. [`crate::from_str_with_options_and_links`]
//! collects one [`LinkInfo`] per link — `LinkType`, destination, and the
//! label's span coordinates in the output text — because ratatui's `Span` has
//! no metadata slot (the side channel IS the design). Wikilinks additionally
//! render label-only: the upstream ` (destination)` suffix is suppressed for
//! [`pulldown_cmark::LinkType::WikiLink`], whose destination duplicates the
//! target and is never a navigable URL.

use pulldown_cmark::{CowStr, Event, LinkType};
use ratatui_core::text::Span;
use tracing::instrument;

use super::TextWriter;
use crate::StyleSheet;

/// Metadata for one rendered link, captured through the side-channel sink
/// (BABYLON PATCH 2).
///
/// `Eq` is not derived because [`LinkType`] only implements `PartialEq`.
#[derive(Debug, Clone, PartialEq)]
pub struct LinkInfo {
    /// The pulldown-cmark link type (wikilink, inline, autolink, …).
    pub link_type: LinkType,
    /// The link destination (for wikilinks: the target page subject).
    pub dest: String,
    /// Where the label sits in the output text; `None` when the link was
    /// rendered inside a buffered construct (table cell, image description)
    /// whose final position the writer cannot know.
    pub location: Option<LinkLocation>,
}

/// Span coordinates of a link label inside the rendered text.
///
/// `start_span` is inclusive within `start_line`; `end_span` is exclusive
/// within `end_line` (the line of the label's last span). A label may cross
/// lines when its source wraps.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkLocation {
    /// Line index of the label's first span.
    pub start_line: usize,
    /// Span index of the label's first span within `start_line`.
    pub start_span: usize,
    /// Line index of the label's last span.
    pub end_line: usize,
    /// Span index just past the label's last span within `end_line`.
    pub end_span: usize,
}

/// A link whose label is currently being rendered (BABYLON PATCH 2: carries
/// the `LinkType` and start position upstream discarded).
#[derive(Debug)]
pub(super) struct PendingLink<'a> {
    pub(super) link_type: LinkType,
    pub(super) dest_url: CowStr<'a>,
    /// `(line, span)` where the label starts, when the main text is the span
    /// sink; `None` inside buffered constructs.
    pub(super) start: Option<(usize, usize)>,
}

impl<'a, 'theme, I, S> TextWriter<'a, 'theme, I, S>
where
    I: Iterator<Item = Event<'a>>,
    S: StyleSheet,
{
    /// Stores the destination and applies the link style to the label.
    #[instrument(level = "trace", skip(self))]
    pub fn push_link(&mut self, link_type: LinkType, dest_url: CowStr<'a>) {
        let start = self.main_flow_position();
        self.link = Some(PendingLink {
            link_type,
            dest_url,
            start,
        });
        self.push_inline_style(self.styles.link());
    }

    /// Restores the enclosing style, records the side-channel metadata, and
    /// appends the destination (except for wikilinks, which render
    /// label-only).
    #[instrument(level = "trace", skip(self))]
    pub fn pop_link(&mut self) {
        self.pop_inline_style();
        if let Some(pending) = self.link.take() {
            let is_wikilink = matches!(pending.link_type, LinkType::WikiLink { .. });
            // Record before any suffix so the location covers the label only.
            let end = self.main_flow_position();
            if let Some(links) = &mut self.links {
                let location = match (pending.start, end) {
                    (Some((start_line, start_span)), Some((end_line, end_span)))
                        if (end_line, end_span) >= (start_line, start_span) =>
                    {
                        Some(LinkLocation {
                            start_line,
                            start_span,
                            end_line,
                            end_span,
                        })
                    }
                    _ => None,
                };
                links.push(LinkInfo {
                    link_type: pending.link_type,
                    dest: pending.dest_url.to_string(),
                    location,
                });
            }
            if !is_wikilink {
                self.push_span(" (".into());
                self.push_span(Span::styled(pending.dest_url, self.styles.link()));
                self.push_span(")".into());
            }
        }
    }

    /// The current `(line, span)` write position in the main output text, or
    /// `None` while a buffered construct (image description, table cell) owns
    /// the span sink (BABYLON PATCH 2).
    fn main_flow_position(&self) -> Option<(usize, usize)> {
        if !self.images.is_empty() || self.table_builder.is_some() {
            return None;
        }
        match self.text.lines.last() {
            Some(line) => Some((self.text.lines.len() - 1, line.spans.len())),
            None => Some((0, 0)),
        }
    }
}

#[cfg(test)]
mod tests {
    use pretty_assertions::assert_eq;
    use rstest::rstest;

    use super::*;
    use crate::renderer::test_support::{with_tracing, DefaultGuard};
    use crate::renderer::*;

    #[rstest]
    fn link_uses_default_style(_with_tracing: DefaultGuard) {
        let link_style = Style::new().blue().underlined();
        assert_eq!(
            from_str("[Link](https://example.com)"),
            Text::from(Line::from_iter([
                Span::styled("Link", link_style),
                Span::from(" ("),
                Span::styled("https://example.com", link_style),
                Span::from(")")
            ]))
        );
    }

    #[rstest]
    fn link_combines_with_bold_style(_with_tracing: DefaultGuard) {
        let link_style = Style::new().blue().underlined();
        assert_eq!(
            from_str("[**Bold link**](https://example.com)"),
            Text::from(Line::from_iter([
                Span::styled("Bold link", link_style.bold()),
                Span::from(" ("),
                Span::styled("https://example.com", link_style),
                Span::from(")"),
            ]))
        );
    }

    #[rstest]
    fn consecutive_links_restore_surrounding_style(_with_tracing: DefaultGuard) {
        let link_style = Style::new().blue().underlined();
        assert_eq!(
            from_str("[One](one) and [Two](two) after"),
            Text::from(Line::from_iter([
                Span::styled("One", link_style),
                Span::raw(" ("),
                Span::styled("one", link_style),
                Span::raw(")"),
                Span::raw(" and "),
                Span::styled("Two", link_style),
                Span::raw(" ("),
                Span::styled("two", link_style),
                Span::raw(")"),
                Span::raw(" after"),
            ]))
        );
    }

    // BABYLON PATCH 2 tests below.

    #[rstest]
    fn side_channel_records_regular_link(_with_tracing: DefaultGuard) {
        let options = Options::default();
        let (text, links) = from_str_with_options_and_links("[One](one) tail", &options);
        assert_eq!(links.len(), 1);
        let info = &links[0];
        assert_eq!(info.dest, "one");
        assert_eq!(info.link_type, LinkType::Inline);
        let loc = info.location.as_ref().expect("main-flow link located");
        let label: String = text.lines[loc.start_line].spans[loc.start_span..loc.end_span]
            .iter()
            .map(|s| s.content.as_ref())
            .collect();
        assert_eq!(label, "One");
    }

    #[rstest]
    fn side_channel_records_wikilink_without_suffix(_with_tracing: DefaultGuard) {
        let options = Options::default().parse_options(pulldown_cmark::Options::ENABLE_WIKILINKS);
        let (text, links) = from_str_with_options_and_links("[[Target|Label]]", &options);
        assert_eq!(links.len(), 1);
        let info = &links[0];
        assert!(matches!(info.link_type, LinkType::WikiLink { .. }));
        assert_eq!(info.dest, "Target");
        let flat: String = text
            .lines
            .iter()
            .flat_map(|l| l.spans.iter())
            .map(|s| s.content.as_ref())
            .collect();
        assert_eq!(flat, "Label", "wikilinks render label-only, no ' (dest)'");
    }

    #[rstest]
    fn plain_entry_points_stay_upstream_shaped(_with_tracing: DefaultGuard) {
        // Without the links-aware entry point, behavior is byte-identical to
        // upstream: no sink allocation, dest suffix still rendered.
        let text = from_str("[One](one)");
        let flat: String = text
            .lines
            .iter()
            .flat_map(|l| l.spans.iter())
            .map(|s| s.content.as_ref())
            .collect();
        assert_eq!(flat, "One (one)");
    }
}
