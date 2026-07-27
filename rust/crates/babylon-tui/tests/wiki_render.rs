//! Contract tests for `wiki_render::render_page` (plan Task 11).
//!
//! These encode the required behavior of the babylon-md fork's two patches:
//! `ENABLE_WIKILINKS` passthrough (patch 1) and link-metadata retention
//! (patch 2). They are written RED against the unpatched vendored crate.

use std::collections::BTreeSet;

use babylon_tui::theme::{CRIMSON, GOLD};
use babylon_tui::wiki_render::{render_page, LinkPosition, LinkSpan};
use ratatui::style::Modifier;
use ratatui::text::Text;

const WIKILINKS: &str = include_str!("fixtures/markdown/wikilinks.md");
const HEADING_FENCE: &str = include_str!("fixtures/markdown/heading_fence.md");
const EMPTY: &str = include_str!("fixtures/markdown/empty.md");

fn known(subjects: &[&str]) -> BTreeSet<String> {
    subjects.iter().map(|s| (*s).to_string()).collect()
}

fn rendered_string(text: &Text) -> String {
    text.lines
        .iter()
        .map(|line| {
            line.spans
                .iter()
                .map(|span| span.content.as_ref())
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Concatenate the span contents a [`LinkPosition`] covers.
fn label_at(text: &Text, pos: &LinkPosition) -> String {
    let mut out = String::new();
    for (line_idx, line) in text.lines.iter().enumerate() {
        if line_idx < pos.start_line || line_idx > pos.end_line {
            continue;
        }
        for (span_idx, span) in line.spans.iter().enumerate() {
            let before_start = line_idx == pos.start_line && span_idx < pos.start_span;
            let past_end = line_idx == pos.end_line && span_idx >= pos.end_span;
            if before_start || past_end {
                continue;
            }
            out.push_str(span.content.as_ref());
        }
    }
    out
}

fn find_link<'a>(links: &'a [LinkSpan], target: &str) -> &'a LinkSpan {
    links
        .iter()
        .find(|l| l.target == target)
        .unwrap_or_else(|| panic!("no LinkSpan for target {target:?} in {links:?}"))
}

#[test]
fn heading_renders_with_heading_style() {
    let (text, _) = render_page(HEADING_FENCE, 80, &known(&[]));
    let flat = rendered_string(&text);
    assert!(
        flat.contains("The Contradiction"),
        "heading text missing from:\n{flat}"
    );
    let heading_line = text
        .lines
        .iter()
        .find(|l| {
            l.spans
                .iter()
                .any(|s| s.content.contains("The Contradiction"))
        })
        .expect("heading line present");
    assert!(
        heading_line.style.add_modifier.contains(Modifier::BOLD),
        "heading line should carry the bold heading style, got {:?}",
        heading_line.style
    );
}

#[test]
fn fence_block_renders_content() {
    let (text, _) = render_page(HEADING_FENCE, 80, &known(&[]));
    let flat = rendered_string(&text);
    assert!(flat.contains("fn main()"), "fence content missing:\n{flat}");
}

#[test]
fn known_wikilink_resolves() {
    let (text, links) = render_page(WIKILINKS, 80, &known(&["Detroit", "Wayne County"]));
    let detroit = find_link(&links, "Detroit");
    assert!(detroit.exists, "Detroit is a known subject");
    assert_eq!(detroit.label, "Detroit", "bare [[t]] labels as the target");
    let pos = detroit.position.as_ref().expect("main-flow link located");
    let span = &text.lines[pos.start_line].spans[pos.start_span];
    assert_eq!(
        span.style.fg,
        Some(GOLD),
        "known wikilinks carry the ksbc gold (ADR099: their own visual \
         register, distinct from ordinary links), got {:?}",
        span.style
    );
}

#[test]
fn aliased_wikilink_keeps_pothole_label() {
    let (_, links) = render_page(WIKILINKS, 80, &known(&["Detroit", "Wayne County"]));
    let county = find_link(&links, "Wayne County");
    assert!(county.exists);
    assert_eq!(county.label, "the county", "[[t|Label]] labels as Label");
}

#[test]
fn unknown_wikilink_is_redlink() {
    let (text, links) = render_page(WIKILINKS, 80, &known(&["Detroit", "Wayne County"]));
    let atlantis = find_link(&links, "Atlantis");
    assert!(!atlantis.exists, "Atlantis is not a known subject");
    let pos = atlantis
        .position
        .as_ref()
        .expect("main-flow link has a position");
    let line = &text.lines[pos.start_line];
    let span = &line.spans[pos.start_span];
    assert_eq!(
        span.style.fg,
        Some(CRIMSON),
        "redlink spans carry the ksbc crimson (ADR099 visual register), got {:?}",
        span.style
    );
}

#[test]
fn positions_point_at_labels() {
    let (text, links) = render_page(WIKILINKS, 80, &known(&["Detroit", "Wayne County"]));
    assert_eq!(links.len(), 3, "three wikilinks in the fixture: {links:?}");
    for link in &links {
        let pos = link
            .position
            .as_ref()
            .unwrap_or_else(|| panic!("main-flow link {link:?} has a position"));
        assert_eq!(
            label_at(&text, pos),
            link.label,
            "position spans reconstruct the label for {link:?}"
        );
    }
}

#[test]
fn wikilinks_render_without_trailing_destination() {
    let (text, _) = render_page(WIKILINKS, 80, &known(&["Detroit", "Wayne County"]));
    let flat = rendered_string(&text);
    assert!(
        !flat.contains("(Detroit)"),
        "wikilinks must not render the upstream ' (dest)' suffix:\n{flat}"
    );
    assert!(
        !flat.contains("(Wayne County)"),
        "aliased wikilinks must not render the target as a suffix:\n{flat}"
    );
}

#[test]
fn empty_page_renders_honest_absence() {
    let (text, links) = render_page(EMPTY, 80, &known(&["Detroit"]));
    assert_eq!(rendered_string(&text), "No content recorded.");
    assert!(links.is_empty());
}
