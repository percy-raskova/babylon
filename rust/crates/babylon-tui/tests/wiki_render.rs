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

// ── The ksbc style sheet (Director feedback 2026-07-27) ──────────────────
// The M3 playtest rejected the stock tui-markdown look ("plain markdown").
// These pin the BabylonStyleSheet's Textual-parity treatment: no literal
// Markdown punctuation, §9b role colors, directive fences kept honest.

/// A vault-shaped page: frontmatter, H1 title, H2 section, directive
/// fences, an anonymous LaTeX-source fence, bullets, inline code.
const VAULT_SHAPED: &str = "---\nid: county/26163\nverified_tick: 500\n---\n# county/26163 — Dossier\n\n## Sovereignty\n\n- claimed by `SOV_USA`\n\n```{statblock} county/26163\npopulation: 1749343\n```\n\n```{absence} energy_beta_j — no producer exists\n```\n\n```\n\\text{LA Ratio} = W_c / V_c\n```\n";

#[test]
fn frontmatter_is_invisible_like_textual() {
    let (text, _) = render_page(VAULT_SHAPED, 80, &known(&[]));
    let flat = rendered_string(&text);
    assert!(
        !flat.contains("verified_tick") && !flat.contains("id: county"),
        "frontmatter must not render (Textual drops front_matter tokens):\n{flat}"
    );
    assert!(
        flat.contains("county/26163 — Dossier"),
        "the body must survive the strip:\n{flat}"
    );
}

#[test]
fn unterminated_frontmatter_is_not_frontmatter() {
    let (text, _) = render_page("---\nnot: closed\n", 80, &known(&[]));
    let flat = rendered_string(&text);
    assert!(
        flat.contains("not: closed"),
        "an unterminated opener renders as body, never silently vanishes:\n{flat}"
    );
}

#[test]
fn frontmatter_only_page_is_honest_absence() {
    let (text, links) = render_page("---\nid: x\n---\n", 80, &known(&[]));
    assert_eq!(rendered_string(&text), "No content recorded.");
    assert!(links.is_empty());
}

#[test]
fn h1_is_crimson_bold_centered_without_marker() {
    let (text, _) = render_page(VAULT_SHAPED, 80, &known(&[]));
    let h1 = text
        .lines
        .iter()
        .find(|l| l.spans.iter().any(|s| s.content.contains("Dossier")))
        .expect("H1 line present");
    assert_eq!(h1.style.fg, Some(CRIMSON), "H1 is crimson: {:?}", h1.style);
    assert!(h1.style.add_modifier.contains(Modifier::BOLD));
    assert_eq!(
        h1.alignment,
        Some(ratatui::layout::Alignment::Center),
        "H1 carries Textual's center alignment"
    );
    let flat = rendered_string(&text);
    assert!(
        !flat.contains("# "),
        "no literal heading markers anywhere:\n{flat}"
    );
}

#[test]
fn h2_is_crimson_underlined() {
    let (text, _) = render_page(VAULT_SHAPED, 80, &known(&[]));
    let h2 = text
        .lines
        .iter()
        .find(|l| l.spans.iter().any(|s| s.content.contains("Sovereignty")))
        .expect("H2 line present");
    assert_eq!(h2.style.fg, Some(CRIMSON));
    assert!(
        h2.style.add_modifier.contains(Modifier::UNDERLINED),
        "H2 is underlined: {:?}",
        h2.style
    );
}

#[test]
fn anonymous_fence_hides_delimiters_and_keeps_the_band() {
    let (text, _) = render_page(VAULT_SHAPED, 80, &known(&[]));
    let flat = rendered_string(&text);
    assert!(
        !flat.contains("```"),
        "no literal fences may render (Textual parity):\n{flat}"
    );
    assert!(
        flat.contains("\\text{LA Ratio}"),
        "the LaTeX-source body must survive:\n{flat}"
    );
    let latex = text
        .lines
        .iter()
        .find(|l| l.spans.iter().any(|s| s.content.contains("LA Ratio")))
        .expect("LaTeX line present");
    assert_eq!(
        latex.style.bg,
        Some(babylon_tui::theme::MUTED_DARK),
        "code-block lines carry the recessed band: {:?}",
        latex.style
    );
}

#[test]
fn directive_fences_keep_their_info_line() {
    let (text, _) = render_page(VAULT_SHAPED, 80, &known(&[]));
    let flat = rendered_string(&text);
    assert!(
        flat.contains("▌{statblock} county/26163"),
        "the statblock header (harness-pinned content) must render:\n{flat}"
    );
    assert!(
        flat.contains("▌{absence} energy_beta_j"),
        "the III.11 absence message lives in the info string:\n{flat}"
    );
    assert!(
        !text.lines.iter().any(|l| {
            let joined: String = l.spans.iter().map(|s| s.content.as_ref()).collect();
            joined == "▌"
        }),
        "no lone closing delimiters — headers only, like Textual's fence widgets:\n{flat}"
    );
    let statblock_header = text
        .lines
        .iter()
        .flat_map(|l| l.spans.iter())
        .find(|s| s.content.contains("{statblock}"))
        .expect("statblock header span");
    assert_eq!(statblock_header.style.fg, Some(GOLD));
    let absence_header = text
        .lines
        .iter()
        .flat_map(|l| l.spans.iter())
        .find(|s| s.content.contains("{absence}"))
        .expect("absence header span");
    assert_eq!(
        absence_header.style.fg,
        Some(CRIMSON),
        "absence headers use the §9b absence-marker role"
    );
}

#[test]
fn bullets_are_crimson_dots() {
    let (text, _) = render_page(VAULT_SHAPED, 80, &known(&[]));
    let bullet = text
        .lines
        .iter()
        .flat_map(|l| l.spans.iter())
        .find(|s| s.content.contains("•"))
        .expect("bullet marker present (never the literal '-')");
    assert_eq!(bullet.style.fg, Some(CRIMSON));
}

#[test]
fn inline_code_is_gold_on_recessed() {
    let (text, _) = render_page(VAULT_SHAPED, 80, &known(&[]));
    let code = text
        .lines
        .iter()
        .flat_map(|l| l.spans.iter())
        .find(|s| s.content.contains("SOV_USA"))
        .expect("inline code span present");
    assert_eq!(code.style.fg, Some(GOLD));
    assert_eq!(code.style.bg, Some(babylon_tui::theme::MUTED_DARK));
}
