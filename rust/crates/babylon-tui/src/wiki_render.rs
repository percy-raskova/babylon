//! Wiki page rendering: babylon-md plus the wikilink → [`LinkSpan`] side
//! channel (plan Task 11).
//!
//! ratatui's `Span` has no metadata slot, so link identity travels OUT OF
//! BAND: [`render_page`] returns the rendered [`Text`] together with a vec of
//! [`LinkSpan`]s whose positions index into that text. The hit registry and
//! hover/peek layers consume the side channel; the text stays plain ratatui.

use std::collections::BTreeSet;

use ratatui::text::Text;

/// One wikilink discovered while rendering a page.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkSpan {
    /// The link target (the page subject the wikilink names).
    pub target: String,
    /// The visible label (`[[t]]` → `t`; `[[t|Label]]` → `Label`).
    pub label: String,
    /// Whether the target is a known page subject (false = redlink).
    pub exists: bool,
    /// Where the label sits in the returned text; `None` when the link was
    /// rendered inside a buffered construct (table cell, image alt) whose
    /// final position babylon-md cannot know.
    pub position: Option<LinkPosition>,
}

/// Span coordinates of a link label inside the rendered [`Text`].
///
/// `start_span` is inclusive, `end_span` is exclusive, both within their
/// respective lines; a label may cross lines when the source wraps.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkPosition {
    /// Line index of the label's first span.
    pub start_line: usize,
    /// Span index of the label's first span within `start_line`.
    pub start_span: usize,
    /// Line index of the label's last span.
    pub end_line: usize,
    /// Span index just past the label's last span within `end_line`.
    pub end_span: usize,
}

/// Render a page's Markdown into ratatui text plus the wikilink side channel.
///
/// `known` is the set of page subjects that exist in the vault: wikilinks
/// whose target is absent from it are redlinks (`exists = false`, styled
/// red). Empty source renders the honest-absence line (Constitution III.11),
/// never a fabricated page. `_width` is reserved for wrap-aware hit mapping
/// (M1 renders unwrapped; the scroll view handles overflow).
pub fn render_page(
    src: &str,
    _width: u16,
    known: &BTreeSet<String>,
) -> (Text<'static>, Vec<LinkSpan>) {
    let src = strip_frontmatter(src);
    if src.trim().is_empty() {
        return (Text::from("No content recorded."), Vec::new());
    }
    let options = babylon_md::Options::new(crate::md_style::BabylonStyleSheet)
        .parse_options(pulldown_cmark::Options::ENABLE_WIKILINKS);
    let (text, infos) = babylon_md::from_str_with_options_and_links(src, &options);
    let mut text = own_text(text);
    let mut links = Vec::new();
    for info in infos {
        if !matches!(info.link_type, pulldown_cmark::LinkType::WikiLink { .. }) {
            continue;
        }
        let target = info.dest;
        let exists = known.contains(&target);
        let position = info.location.map(|loc| LinkPosition {
            start_line: loc.start_line,
            start_span: loc.start_span,
            end_line: loc.end_line,
            end_span: loc.end_span,
        });
        let label = match &position {
            Some(pos) => label_at(&text, pos),
            // Buffered constructs lose position AND label; the target is the
            // only honest stand-in (bare wikilinks label as their target).
            None => target.clone(),
        };
        if let Some(pos) = &position {
            let color = if exists {
                crate::theme::GOLD
            } else {
                crate::theme::CRIMSON
            };
            restyle_link(&mut text, pos, color);
        }
        links.push(LinkSpan {
            target,
            label,
            exists,
            position,
        });
    }
    (text, links)
}

/// Strip one leading YAML frontmatter block (`---` … `---` at the very top).
///
/// Textual parity: the vault bakes frontmatter onto every page, but the
/// Textual client tokenizes it with the `front_matter` plugin (ADR099) and
/// its Markdown widget never renders those tokens — frontmatter is
/// invisible there. Without this strip the Rust side mis-parses the block
/// as body markdown (a thematic break plus a phantom setext heading). An
/// unterminated opener is NOT frontmatter — the source renders unchanged.
fn strip_frontmatter(src: &str) -> &str {
    let Some(rest) = src.strip_prefix("---\n") else {
        return src;
    };
    let mut consumed = 0usize;
    for line in rest.split_inclusive('\n') {
        consumed += line.len();
        if line.trim_end_matches(['\r', '\n']) == "---" {
            return &rest[consumed..];
        }
    }
    src
}

/// Concatenate the span contents a [`LinkPosition`] covers.
fn label_at(text: &Text<'_>, pos: &LinkPosition) -> String {
    let mut out = String::new();
    for (line_idx, line) in text.lines.iter().enumerate() {
        if line_idx < pos.start_line || line_idx > pos.end_line {
            continue;
        }
        for (span_idx, span) in line.spans.iter().enumerate() {
            let before_start = line_idx == pos.start_line && span_idx < pos.start_span;
            let past_end = line_idx == pos.end_line && span_idx >= pos.end_span;
            if !(before_start || past_end) {
                out.push_str(span.content.as_ref());
            }
        }
    }
    out
}

/// Restyle the spans a link label covers (ADR099: wikilinks carry their own
/// visual register — gold for known targets, crimson for redlinks — instead
/// of piggy-backing on the ordinary-link style).
fn restyle_link(text: &mut Text<'static>, pos: &LinkPosition, color: ratatui::style::Color) {
    for (line_idx, line) in text.lines.iter_mut().enumerate() {
        if line_idx < pos.start_line || line_idx > pos.end_line {
            continue;
        }
        for (span_idx, span) in line.spans.iter_mut().enumerate() {
            let before_start = line_idx == pos.start_line && span_idx < pos.start_span;
            let past_end = line_idx == pos.end_line && span_idx >= pos.end_span;
            if !(before_start || past_end) {
                span.style = span.style.fg(color);
            }
        }
    }
}

/// Deep-copy a borrowed [`Text`] into an owned `Text<'static>`.
fn own_text(text: Text<'_>) -> Text<'static> {
    Text {
        lines: text
            .lines
            .into_iter()
            .map(|line| ratatui::text::Line {
                spans: line
                    .spans
                    .into_iter()
                    .map(|span| ratatui::text::Span {
                        content: span.content.into_owned().into(),
                        style: span.style,
                    })
                    .collect(),
                style: line.style,
                alignment: line.alignment,
            })
            .collect(),
        style: text.style,
        alignment: text.alignment,
    }
}
