//! Ports `tests/unit/tui/test_router.py` (babylon.tui.router) verbatim: every
//! input/expected pair from the Python case table, against the Rust
//! `BabylonTarget` enum contract (`Entity`/`Kind`/`Redlink`, not the Python
//! module's `kind`/`entity_id`/`redlink` struct fields — see router.rs docs
//! for the mapping).

use babylon_tui::router::{format_babylon_uri, parse_babylon_uri, BabylonTarget, RouterError};

// --- TestParseBabylonUri -----------------------------------------------

#[test]
fn it_parses_an_explicit_kind_href() {
    let target = parse_babylon_uri("babylon://county/26163").unwrap();
    assert_eq!(
        target,
        BabylonTarget::Kind {
            kind: "county".to_string(),
            id: "26163".to_string(),
        }
    );
}

#[test]
fn it_parses_a_fully_bare_href_with_no_slash() {
    let target = parse_babylon_uri("babylon://uaw-600").unwrap();
    assert_eq!(target, BabylonTarget::Entity("uaw-600".to_string()));
}

#[test]
fn it_parses_a_redlink_href() {
    let target = parse_babylon_uri("babylon://redlink/org/uaw-9999").unwrap();
    assert_eq!(target, BabylonTarget::Redlink("org/uaw-9999".to_string()));
}

#[test]
fn it_parses_a_redlink_href_with_a_single_token_target() {
    let target = parse_babylon_uri("babylon://redlink/uaw-9999").unwrap();
    assert_eq!(target, BabylonTarget::Redlink("uaw-9999".to_string()));
}

#[test]
fn it_rejects_a_non_babylon_scheme() {
    let err = parse_babylon_uri("http://county/26163").unwrap_err();
    assert!(matches!(err, RouterError::NotBabylonScheme(_)));
    assert!(err.to_string().contains("not a babylon"));
}

#[test]
fn it_rejects_a_uri_with_no_host_segment() {
    let err = parse_babylon_uri("babylon:///26163").unwrap_err();
    assert!(matches!(err, RouterError::MissingHost(_)));
    assert!(err.to_string().contains("missing host"));
}

#[test]
fn it_rejects_a_malformed_id_segment() {
    let err = parse_babylon_uri("babylon://county/26 163").unwrap_err();
    assert!(matches!(err, RouterError::MalformedEntityId(_)));
    assert!(err.to_string().contains("malformed"));
}

#[test]
fn it_rejects_a_malformed_kind_segment() {
    let err = parse_babylon_uri("babylon://coun ty/26163").unwrap_err();
    assert!(matches!(err, RouterError::MalformedKind(_)));
    assert!(err.to_string().contains("malformed"));
}

#[test]
fn it_rejects_an_empty_string() {
    let err = parse_babylon_uri("").unwrap_err();
    assert!(matches!(err, RouterError::NotBabylonScheme(_)));
}

// --- TestFormatBabylonUri -----------------------------------------------

#[test]
fn it_round_trips_an_explicit_kind_target() {
    let target = parse_babylon_uri("babylon://county/26163").unwrap();
    let round_tripped = parse_babylon_uri(&format_babylon_uri(&target)).unwrap();
    assert_eq!(round_tripped, target);
}

#[test]
fn it_round_trips_a_redlink_target() {
    let target = parse_babylon_uri("babylon://redlink/org/uaw-9999").unwrap();
    let round_tripped = parse_babylon_uri(&format_babylon_uri(&target)).unwrap();
    assert_eq!(round_tripped, target);
}

#[test]
fn it_round_trips_a_bare_wikilink_target() {
    let target = parse_babylon_uri("babylon://uaw-600").unwrap();
    let round_tripped = parse_babylon_uri(&format_babylon_uri(&target)).unwrap();
    assert_eq!(round_tripped, target);
}

#[test]
fn it_formats_the_bare_form_through_the_wikilink_sentinel_like_python() {
    // Python's format_babylon_uri emits `prefix = target.kind` and the bare
    // kind IS "wikilink" — cross-implementation strings must round-trip.
    let target = parse_babylon_uri("babylon://uaw-600").unwrap();
    assert_eq!(format_babylon_uri(&target), "babylon://wikilink/uaw-600");
}

#[test]
fn it_parses_the_python_emitted_sentinel_form_as_a_bare_entity() {
    assert_eq!(
        parse_babylon_uri("babylon://wikilink/uaw-600").unwrap(),
        BabylonTarget::Entity("uaw-600".to_string()),
        "the sentinel-prefixed bare form is the SAME target as babylon://uaw-600"
    );
}

// --- TestBabylonTarget ---------------------------------------------------
//
// The Python suite's `test_it_is_frozen`, `test_it_rejects_an_empty_kind`,
// and `test_it_rejects_an_empty_entity_id` exercise direct construction of
// the pydantic `BabylonTarget` model (frozen + field validators). The Rust
// `BabylonTarget` is a plain enum with no direct-construction validation —
// those invariants aren't reachable through the pinned contract's surface,
// only through `parse_babylon_uri`, whose character-class regexes already
// require at least one character in every segment they accept. See this
// test file's module doc and the final report for the deviation note.
