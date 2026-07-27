//! Wikilink semantics parity table (plan Task 12).
//!
//! Ports the behavior TABLE from `tests/unit/tui/test_wikilinks.py`
//! (`babylon.tui.wikilinks`, the markdown-it-py inline rule + Textual
//! content-span mixin) as contract tests over `render_page`
//! (`babylon_tui::wiki_render`). Rev 2 of the plan retires the custom
//! `[[target]]` scanning rule entirely: pulldown-cmark 0.13's **native**
//! `ENABLE_WIKILINKS` extension does the parsing, so there is no scanning
//! code to write here — these tests exist to pin what `render_page` must DO
//! with the events that extension emits, exactly as the Python suite pinned
//! `wikilink_plugin`/`WikilinkContentMixin`.
//!
//! Field mapping from the Python token pair to the Rust `LinkSpan`:
//!
//! | Python                                             | Rust                        |
//! |-----------------------------------------------------|-----------------------------|
//! | `text_token.content` (the alias, or target if none) | `LinkSpan::label`           |
//! | the wikilink's raw target (pre-`href` string)        | `LinkSpan::target`          |
//! | `kind == "wikilink"` (`resolver(target)` truthy)     | `LinkSpan::exists == true`  |
//! | `kind == "redlink"` (`resolver(target)` falsy)       | `LinkSpan::exists == false` |
//!
//! Python builds a `babylon://<target>` / `babylon://redlink/<target>` `href`
//! string directly in the inline rule. The Rust split moves that
//! construction to `router::format_babylon_uri` (Task 13): `render_page`
//! itself only ever hands back the BARE target text — never a `babylon://`
//! scheme, never a `redlink/` path segment baked into `target` — leaving
//! `exists` as the sole discriminant. Every test below that checks a target
//! also asserts that invariant, since a stray prefix baked into `target`
//! would silently break `router::parse_babylon_uri` round-tripping.
//!
//! Python's `_ContentBuilder` span-based styling (`WIKILINK_COLOR` /
//! `REDLINK_COLOR`, the `@click` meta) has no Rust analogue to assert against
//! here: per the task brief, style is asserted ONLY via `exists` (the
//! redlink case), never a specific color — `render_page`'s caller decides
//! how `exists` maps to a color.
//!
//! ## Two upstream pulldown-cmark parser quirks (for content authors)
//!
//! Both are documented at
//! <https://github.com/pulldown-cmark/pulldown-cmark/blob/main/pulldown-cmark/specs/wikilinks.txt>
//! and have no Python-side equivalent (the old `WIKILINK_RE` regex had
//! different — simpler, and in one case stricter — rules; native
//! `ENABLE_WIKILINKS` is now the sole authority):
//!
//! 1. **A pipe cannot be backslash-escaped inside a wikilink.** Unlike table
//!    cells or emphasis, `\|` inside `[[...]]` does NOT produce a literal
//!    `|` in the target. The pipe still delimits target/label, and the
//!    backslash is retained literally as part of the target text — e.g.
//!    `[[first\|second]]` parses as target `` first\ `` (trailing literal
//!    backslash) / label `second`, matching pulldown-cmark's chosen
//!    (commonmark-hs-style) behavior. Content authors who want a literal `|`
//!    in a page id have no escape hatch; don't use `|` in entity ids.
//! 2. **Empty or malformed `[[...]]` renders as literal text**, not a link:
//!    `[[]]`, `[[|]]`, `[[|Symbol]]`, an unmatched `[[` or `]]` — none of
//!    these produce a `LinkSpan`; the brackets and any inner text pass
//!    through into the rendered page verbatim.

use std::collections::BTreeSet;

use babylon_tui::wiki_render::render_page;

/// Build a `known`-subjects set from string literals (test convenience only;
/// production code fills this from `Host::known_subjects_json`).
fn known(subjects: &[&str]) -> BTreeSet<String> {
    subjects.iter().map(|s| s.to_string()).collect()
}

/// A `known` set wide enough for tests that don't care about existence.
fn no_subjects() -> BTreeSet<String> {
    BTreeSet::new()
}

/// Every target/label/redlink assertion below also checks this: `target`
/// must never carry a `babylon://` scheme or a `redlink/` segment — URI
/// construction is `router::format_babylon_uri`'s job, not `render_page`'s.
fn assert_bare_target(target: &str) {
    assert!(
        !target.contains("babylon://"),
        "LinkSpan::target must be bare, got {target:?}"
    );
    assert!(
        !target.contains("redlink/"),
        "LinkSpan::target must not bake in the redlink path segment, got {target:?}"
    );
}

// --- Bare wikilink, known target ---------------------------------------
// Ports test_it_emits_wikilink_tokens_for_a_known_target.

#[test]
fn bare_wikilink_to_a_known_target_is_a_wikilink_span() {
    let (text, spans) = render_page("[[county/26163]]", 80, &known(&["county/26163"]));

    assert_eq!(spans.len(), 1);
    let span = &spans[0];
    assert_eq!(span.target, "county/26163");
    assert_eq!(span.label, "county/26163");
    assert!(span.exists);
    assert_bare_target(&span.target);

    assert_eq!(text.to_string(), "county/26163");
    assert!(
        span.position.is_some(),
        "an inline link must carry a position"
    );
    assert_eq!(span.position.as_ref().unwrap().start_line, 0);
}

// --- Bare wikilink, unknown target (redlink) ---------------------------
// Ports test_it_emits_redlink_tokens_for_an_unknown_target.

#[test]
fn bare_wikilink_to_an_unknown_target_is_a_redlink_span() {
    let (text, spans) = render_page("[[org/uaw-9999]]", 80, &no_subjects());

    assert_eq!(spans.len(), 1);
    let span = &spans[0];
    assert_eq!(span.target, "org/uaw-9999");
    assert_eq!(span.label, "org/uaw-9999");
    assert!(
        !span.exists,
        "unknown target must be a redlink: exists == false"
    );
    assert_bare_target(&span.target);

    assert_eq!(text.to_string(), "org/uaw-9999");
}

// --- Aliased wikilink ---------------------------------------------------
// Ports test_it_uses_the_alias_as_display_text.

#[test]
fn aliased_wikilink_uses_the_alias_as_the_label_but_keeps_the_real_target() {
    let (text, spans) = render_page(
        "[[county/26163|Wayne County]]",
        80,
        &known(&["county/26163"]),
    );

    assert_eq!(spans.len(), 1);
    let span = &spans[0];
    assert_eq!(span.target, "county/26163");
    assert_eq!(span.label, "Wayne County");
    assert!(span.exists);

    assert_eq!(text.to_string(), "Wayne County");
}

// --- Aliased redlink -----------------------------------------------------
// Combines the alias case with the redlink case (both independently
// pinned above by the Python table; this checks they compose).

#[test]
fn aliased_wikilink_to_an_unknown_target_is_still_a_redlink() {
    let (_text, spans) = render_page(
        "[[org/uaw-9999|The UAW Local]]",
        80,
        &known(&["county/26163"]),
    );

    assert_eq!(spans.len(), 1);
    let span = &spans[0];
    assert_eq!(span.target, "org/uaw-9999");
    assert_eq!(span.label, "The UAW Local");
    assert!(!span.exists);
}

// --- `known` is the sole existence authority ---------------------------
// Ports the parametrization implied by known_target_resolver: the SAME
// source's existence flips purely with the `known` argument.

#[test]
fn existence_is_determined_solely_by_the_known_parameter() {
    let source = "[[org/uaw-9999]]";

    let (_t, absent) = render_page(source, 80, &no_subjects());
    assert!(!absent[0].exists);

    let (_t, present) = render_page(source, 80, &known(&["org/uaw-9999"]));
    assert!(present[0].exists);
}

#[test]
fn known_matching_is_exact_not_case_insensitive() {
    // Not in the Python table (the old resolver was also exact-match via
    // frozenset membership) but worth pinning explicitly: `known` is an
    // *exact* BTreeSet<String> membership test, not a case-folded one.
    let (_text, spans) = render_page("[[county/26163]]", 80, &known(&["COUNTY/26163"]));
    assert!(!spans[0].exists);
}

// --- Ordinary markdown links are left untouched -------------------------
// Ports test_it_leaves_ordinary_links_untouched: an `[text](url)` inline
// link is NOT a wikilink and must not produce a LinkSpan (hit-registry
// wiring is a wikilink-only side channel; see the `LinkSpan` doc comment).

#[test]
fn ordinary_markdown_links_produce_no_link_span() {
    let (text, spans) = render_page("[a link](http://example.com)", 80, &no_subjects());

    assert!(
        spans.is_empty(),
        "an ordinary (non-wikilink) link must not appear in the wikilink side channel"
    );
    assert!(text.to_string().contains("a link"));
}

// --- Emphasis still renders as upstream babylon-md/tui-markdown does ----
// Ports test_it_still_handles_emphasis_as_upstream_does: a sanity check
// that plain markdown formatting is untouched and, in particular, does not
// spuriously produce a LinkSpan.

#[test]
fn emphasis_renders_plain_text_with_no_link_span() {
    let (text, spans) = render_page("*urgent*", 80, &no_subjects());

    assert!(spans.is_empty());
    assert!(text.to_string().contains("urgent"));
}

// --- Multiple wikilinks in one page: order and independence -------------
// Not a single Python test, but the direct consequence of applying the
// per-link rule above to more than one link in the same page: order must
// match source order (the hit registry depends on this) and each link's
// existence is independent.

#[test]
fn multiple_wikilinks_are_reported_in_source_order_independently() {
    let (_text, spans) = render_page(
        "[[county/26163]] and [[org/uaw-9999]]",
        80,
        &known(&["county/26163"]),
    );

    assert_eq!(spans.len(), 2);
    assert_eq!(spans[0].target, "county/26163");
    assert!(spans[0].exists);
    assert_eq!(spans[1].target, "org/uaw-9999");
    assert!(!spans[1].exists);
}

// --- Quirk 1: a pipe cannot be backslash-escaped inside a wikilink -------
// New in the Rust port (native ENABLE_WIKILINKS behavior; the old WIKILINK_RE
// had no escaping concept at all since `|` was simply excluded from the
// target character class). Per the upstream spec, `[[first\|second]]`
// still splits on the pipe; the backslash survives literally as part of
// the target rather than escaping it away.

#[test]
fn a_pipe_cannot_be_backslash_escaped_inside_a_wikilink() {
    let (text, spans) = render_page(r"[[first\|second]]", 80, &known(&[r"first\"]));

    assert_eq!(spans.len(), 1);
    let span = &spans[0];
    assert_eq!(
        span.target, r"first\",
        "the backslash is retained literally, not consumed as an escape"
    );
    assert_eq!(span.label, "second");
    assert!(
        span.exists,
        "existence check must match against the raw (unencoded) target, backslash included"
    );
    assert_bare_target(&span.target);

    assert_eq!(text.to_string(), "second");
}

// --- Quirk 2: empty / malformed wikilinks render as literal text --------

#[test]
fn an_empty_wikilink_renders_as_literal_text_not_a_link() {
    let (text, spans) = render_page("[[]]", 80, &no_subjects());

    assert!(spans.is_empty(), "[[]] must not produce a LinkSpan");
    assert_eq!(text.to_string(), "[[]]");
}

#[test]
fn malformed_wikilink_variants_all_render_literally() {
    // Verbatim fixture from the upstream pulldown-cmark spec
    // (specs/wikilinks.txt, "Empty or Invalid Wikilinks"): every one of
    // these is malformed (empty target, empty-target-with-pipe, pipe with
    // no target before it, an unmatched opening `[[`) and none of them
    // produce a link.
    let source = "]] [[]] [[|]] [[|Symbol]] [[";
    let (text, spans) = render_page(source, 80, &no_subjects());

    assert!(spans.is_empty());
    assert_eq!(text.to_string(), source);
}
