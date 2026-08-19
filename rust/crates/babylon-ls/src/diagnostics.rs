//! The mapping layer (issue #652 Task 6, plan §6.2/§6.4): `PrepareError`/
//! `ScenarioError`/`ReadError` → [`lsp_types::Diagnostic`] — code, severity,
//! source, `data.{family,precision}` (no `d_records`, wave 2 per §6.2's own
//! carve-out), the declared total order, and the `Vec<Diagnostic>` builder.
//! Push ([`crate::lifecycle`]'s `publishDiagnostics`) and pull
//! (`textDocument/diagnostic`, `workspace/diagnostic`) both call through
//! here — ONE mapping, two delivery mechanisms (§6.1).
//!
//! **Observes-only (global constraint 1).** Every fact this module reports
//! was already computed by the loader (`babylon-bsl`/`babylon-tick`); this
//! module never re-implements or widens a check — it maps what the loader
//! already refused to LSP shape. **Never scans a message string for
//! location or code** (sentinel 7.2) — every field read here is a typed
//! field on the loader's own error type.
//!
//! # The wave-1 precision table (§6.6)
//!
//! | Family | Wave-1 precision | Mechanism |
//! |---|---|---|
//! | `E-LEX` (13 codes) | **Exact** | `ReadError`'s own `position`, expanded to the enclosing token's byte range by [`token_span_at`] — a local re-scan over `text`, not `SpanTable::innermost_at`: a read failure never produces a `SpanTable` at all (`read_all_spanned` discards its partial `entries` on the `?` that propagates the error, `reader.rs:383-397`), so there is no table to query for the one error this tier exists to locate. |
//! | Any error carrying an [`ErrorIdentity`] (§2.3) | **Form** | One of [`crate::locator`]'s four strategies, dispatched by [`crate::locator::locate`]. Unique match ⇒ that span. Ambiguous ⇒ file-level range plus one `relatedInformation` entry per candidate, sorted into document order. Absent ⇒ file-level, no `relatedInformation`. `data.precision` reads `"form"` regardless of which of the three outcomes the search landed on — it names the error's own CLASS (it carries typed identity at all), not the search's runtime luck. |
//! | `E-TYPE` (15 codes) | **File** | `TypeError` is `{code, message}` with no struct variants (`typecheck.rs:81-85`) — nothing to locate. Wave 2 gives it identity at the raise site. |
//! | Prose-only variants (`Malformed{message}` in six modules; `DomainError::Undeterminable{candidates}`) | **File** (`Undeterminable` ⇒ file + `relatedInformation`, via [`ErrorIdentity::Ambiguous`]) | By construction: the loader names no single token. |
//! | `E-EVAL` reached with no live session | **File**, distinct message | Not reachable from [`babylon_tick::diagnose_content_set`] today — evaluation never runs during a diagnostic pass (load-time checks only); documented for completeness, unimplemented here because nothing produces it yet (the same disclosed-gap discipline as [`crate::locator`]'s `ErrorIdentity::Edge` note). |

use lsp_types::{
    Diagnostic, DiagnosticRelatedInformation, DiagnosticSeverity, Location, NumberOrString, Range,
    Url,
};

use babylon_bsl::rule_pipeline::LoadError;
use babylon_bsl::scenario::ScenarioError;
use babylon_bsl::{read_all_spanned, ErrorIdentity, SExpr, SpanTable};
use babylon_tick::PrepareError;

use crate::line_index::LineIndex;
use crate::locator::{locate, LocateOutcome};

/// `data.precision` (§6.2's own three wave-1 tiers).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Precision {
    /// `E-LEX`: the exact offending token's span.
    Exact,
    /// Any error carrying an [`ErrorIdentity`]: a located form's span, or a
    /// documented fallback to file level (ambiguous/absent).
    Form,
    /// `E-TYPE`, prose-only variants, or (wave 2) `E-EVAL`: no locatable
    /// token at all — the whole file.
    File,
}

impl Precision {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Exact => "exact",
            Self::Form => "form",
            Self::File => "file",
        }
    }
}

/// A normalized view of one loader refusal, built by one adapter per
/// concrete error type (§6.4) — everything [`map_to_diagnostic`] needs,
/// independent of which loader stage raised it.
#[derive(Debug, Clone)]
pub struct Located {
    /// `spec_code()` verbatim, or `None` where the loader names none
    /// (never invented, §6.2).
    pub code: Option<&'static str>,
    /// WHAT the error is about, when the loader can name it.
    pub identity: Option<ErrorIdentity>,
    /// The byte offset a `ReadError` (`E-LEX`) detected the failure at.
    pub position: Option<usize>,
    /// Human-readable detail (the loader's own `Display`).
    pub message: String,
    /// Error for a refusal — every wave-1 producer is one (§6.2).
    pub severity: DiagnosticSeverity,
}

impl Located {
    /// Adapt one `LoadError` (`babylon-bsl`'s rule-load rejection type).
    #[must_use]
    pub fn from_load_error(err: &LoadError) -> Self {
        let position = match err {
            LoadError::Read(read_error) => Some(read_error.position),
            _ => None,
        };
        Self {
            code: err.spec_code(),
            identity: babylon_bsl::identity_of(err),
            position,
            message: err.to_string(),
            severity: DiagnosticSeverity::ERROR,
        }
    }

    /// Adapt one `ScenarioError` (`babylon-bsl`'s `.bscn`-load rejection
    /// type).
    #[must_use]
    pub fn from_scenario_error(err: &ScenarioError) -> Self {
        Self {
            code: err.code,
            identity: err.identity.clone(),
            position: err.position,
            message: err.to_string(),
            severity: DiagnosticSeverity::ERROR,
        }
    }

    /// `PrepareError` wraps `LoadError`/`ScenarioError`/`DeclError`, or
    /// (`Composition`) carries `code`/`identity` directly as data (Task 3,
    /// #652) — one delegate per variant, wildcard-free so a new
    /// `PrepareError` variant is a compile error here too.
    #[must_use]
    pub fn from_prepare_error(err: &PrepareError) -> Self {
        match err {
            PrepareError::Scenario(scenario_error) => Self::from_scenario_error(scenario_error),
            PrepareError::Rule { error, .. } => Self::from_load_error(error),
            PrepareError::Intrinsic(decl_error) => {
                // `decl_identity` is `pub(crate)` inside `babylon-bsl`; the
                // crate's own public, wildcard-free `identity_of` already
                // covers `DeclError` via `LoadError::Intrinsic` — reuse
                // that public surface rather than widening a private one.
                let wrapped = LoadError::Intrinsic(decl_error.clone());
                Self {
                    code: decl_error.spec_code(),
                    identity: babylon_bsl::identity_of(&wrapped),
                    position: None,
                    message: err.to_string(),
                    severity: DiagnosticSeverity::ERROR,
                }
            }
            PrepareError::Composition {
                code,
                identity,
                message,
            } => Self {
                code: *code,
                identity: identity.clone(),
                position: None,
                message: message.clone(),
                severity: DiagnosticSeverity::ERROR,
            },
        }
    }
}

/// This error's precision tier, from its own shape — independent of
/// whether locating it at runtime actually found a unique span (§6.6's
/// table: `data.precision` is a static fact about the error CLASS).
#[must_use]
pub fn precision_of(located: &Located) -> Precision {
    if located.position.is_some() {
        Precision::Exact
    } else if located.identity.is_some() {
        Precision::Form
    } else {
        Precision::File
    }
}

/// The byte range of the token containing (or starting at) `position`,
/// scanning `text` directly — the E-LEX tier's own mechanism (see this
/// module's doc for why it does not use [`SpanTable::innermost_at`]).
/// Bounded by `text.len()` in both directions (Power-of-10 rule 2).
#[must_use]
pub fn token_span_at(text: &str, position: usize) -> (usize, usize) {
    let bytes = text.as_bytes();
    let position = position.min(bytes.len());
    if position >= bytes.len() || is_boundary_byte(bytes[position]) {
        // A delimiter, or past end of text: a one-byte (or empty, at EOF)
        // span at `position` itself — nothing wider to claim.
        return (position, (position + 1).min(bytes.len()).max(position));
    }
    let mut start = position;
    while start > 0 && !is_boundary_byte(bytes[start - 1]) {
        start -= 1;
    }
    let mut end = position;
    while end < bytes.len() && !is_boundary_byte(bytes[end]) {
        end += 1;
    }
    (start, end)
}

/// The same token-boundary alphabet the reader's own `is_delimiter` uses
/// (`reader.rs`): whitespace, `(`, `)`, `;` (comment start). ASCII-only
/// check on a raw byte is safe here because every one of these boundary
/// characters is a single ASCII byte in UTF-8, so it can never land mid
/// multi-byte sequence.
fn is_boundary_byte(b: u8) -> bool {
    matches!(b, b' ' | b'\t' | b'\n' | b'\r' | b'(' | b')' | b';')
}

/// Convert a byte range into `text` to an LSP [`Range`] via `line_index`.
fn byte_range_to_lsp_range(text: &str, line_index: &LineIndex, start: usize, end: usize) -> Range {
    let start_u32 = u32::try_from(start).unwrap_or(u32::MAX);
    let end_u32 = u32::try_from(end).unwrap_or(u32::MAX);
    Range {
        start: line_index.offset_to_position(text, start_u32),
        end: line_index.offset_to_position(text, end_u32),
    }
}

/// The whole-file range (`0..text.len()`), used for every File-tier
/// diagnostic and for the primary range of an Ambiguous/Absent Form-tier
/// outcome.
fn file_range(text: &str, line_index: &LineIndex) -> Range {
    byte_range_to_lsp_range(text, line_index, 0, text.len())
}

/// Map one [`Located`] refusal to a [`Diagnostic`] for `uri`/`text`,
/// locating it against `parsed` (this file's own `(forest, SpanTable)`,
/// when reading `text` succeeded — `None` when it did not, in which case
/// every Form-tier identity search degrades to file level by construction:
/// there is no tree left to search).
#[must_use]
pub fn map_to_diagnostic(
    uri: &Url,
    text: &str,
    line_index: &LineIndex,
    parsed: Option<&(Vec<SExpr>, SpanTable)>,
    located: &Located,
) -> Diagnostic {
    let precision = precision_of(located);
    let (range, related_information) = match (precision, located.position, &located.identity) {
        (Precision::Exact, Some(position), _) => {
            let (start, end) = token_span_at(text, position);
            (byte_range_to_lsp_range(text, line_index, start, end), None)
        }
        (Precision::Form, _, Some(identity)) => match parsed {
            Some((forest, spans)) => match locate(identity, forest, spans) {
                LocateOutcome::Unique(span) => (
                    byte_range_to_lsp_range(text, line_index, span.start, span.end),
                    None,
                ),
                LocateOutcome::Ambiguous(candidates) => {
                    let related = candidates
                        .iter()
                        .map(|span| DiagnosticRelatedInformation {
                            location: Location {
                                uri: uri.clone(),
                                range: byte_range_to_lsp_range(
                                    text, line_index, span.start, span.end,
                                ),
                            },
                            message: "another declaration of the same name".to_owned(),
                        })
                        .collect();
                    (file_range(text, line_index), Some(related))
                }
                LocateOutcome::Absent => (file_range(text, line_index), None),
            },
            None => (file_range(text, line_index), None),
        },
        _ => (file_range(text, line_index), None),
    };
    Diagnostic {
        range,
        severity: Some(located.severity),
        code: located.code.map(|c| NumberOrString::String(c.to_owned())),
        code_description: None,
        source: Some("bsl".to_owned()),
        message: located.message.clone(),
        related_information,
        tags: None,
        data: Some(serde_json::json!({
            "precision": precision.as_str(),
        })),
    }
}

/// The server's own "no content set declares this file" notice (§6.1,
/// §6.3) — not a loader refusal, so it never goes through [`Located`]/
/// [`map_to_diagnostic`]: `source`/`severity` are fixed, there is no
/// `code`, and `data` carries no `precision` (this is not one of the
/// loader's own tiers).
#[must_use]
pub fn missing_manifest_row_diagnostic(
    text: &str,
    line_index: &LineIndex,
    path: &str,
) -> Diagnostic {
    Diagnostic {
        range: file_range(text, line_index),
        severity: Some(DiagnosticSeverity::INFORMATION),
        code: None,
        code_description: None,
        source: Some("bsl".to_owned()),
        message: format!(
            "{path} names no row in content-sets.toml — only declaration-independent \
             checks run (read, split_content, surface/:material-basis, static shape); \
             this is also a manifest-drift alarm"
        ),
        related_information: None,
        tags: None,
        data: None,
    }
}

/// The declared total order (§6.2): `(range.start, range.end, code,
/// message)` — deterministic serialization independent of the order
/// `errors` arrived in.
#[must_use]
pub fn sort_key(d: &Diagnostic) -> (u32, u32, u32, u32, String, String) {
    let code = match &d.code {
        Some(NumberOrString::String(s)) => s.clone(),
        Some(NumberOrString::Number(n)) => n.to_string(),
        None => String::new(),
    };
    (
        d.range.start.line,
        d.range.start.character,
        d.range.end.line,
        d.range.end.character,
        code,
        d.message.clone(),
    )
}

/// Build the full `Vec<Diagnostic>` for one file: locate every `located`
/// refusal against `text`'s own `(forest, SpanTable)` (re-read once, here
/// — `babylon-bsl`'s own reader, per the global constraint that this
/// crate owns no parsing of its own), and sort into the declared total
/// order. Bounded by `located.len()` (Power-of-10 rule 2).
#[must_use]
pub fn diagnostics_for_file(
    uri: &Url,
    text: &str,
    line_index: &LineIndex,
    located: &[Located],
) -> Vec<Diagnostic> {
    let parsed = read_all_spanned(text.as_bytes()).ok();
    let mut diagnostics: Vec<Diagnostic> = located
        .iter()
        .map(|loc| map_to_diagnostic(uri, text, line_index, parsed.as_ref(), loc))
        .collect();
    diagnostics.sort_by_key(sort_key);
    diagnostics
}

/// `resultId` (§6.1): `sha256` over the ordered `(uri, bytes)` tuples of a
/// content set plus the manifest bytes — deterministic across restarts (a
/// monotonic counter would have been state, and wrong). `entries` must
/// already be caller-sorted by `uri` (this function does not sort — the
/// caller controls the ordering source, e.g. a `BTreeMap` walk, keeping
/// the sort visible at the call site rather than hidden in here).
#[must_use]
pub fn compute_result_id(entries: &[(&Url, &[u8])], manifest_bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    use std::fmt::Write as _;
    let mut hasher = Sha256::new();
    for (uri, bytes) in entries {
        hasher.update(uri.as_str().as_bytes());
        hasher.update([0u8]); // a NUL separator: no valid URI byte is NUL.
        hasher.update(bytes);
        hasher.update([0u8]);
    }
    hasher.update(manifest_bytes);
    let digest = hasher.finalize();
    let mut out = String::with_capacity(digest.len() * 2);
    for byte in digest {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

#[cfg(test)]
mod tests {
    use super::{
        compute_result_id, diagnostics_for_file, missing_manifest_row_diagnostic, precision_of,
        token_span_at, Located, Precision,
    };
    use crate::line_index::LineIndex;
    use babylon_bsl::rule_pipeline::LoadError;
    use babylon_bsl::{read, ErrorIdentity};
    use lsp_types::{DiagnosticSeverity, Url};

    fn uri() -> Url {
        Url::parse("file:///a.bsl").expect("valid test URI")
    }

    #[test]
    fn precision_exact_when_position_is_set() {
        let located = Located {
            code: Some("E-LEX-003"),
            identity: None,
            position: Some(3),
            message: "bad token".to_owned(),
            severity: DiagnosticSeverity::ERROR,
        };
        assert_eq!(precision_of(&located), Precision::Exact);
    }

    #[test]
    fn precision_form_when_identity_is_set_and_position_is_not() {
        let located = Located {
            code: Some("E-LOAD-001"),
            identity: Some(ErrorIdentity::Name("foo".to_owned())),
            position: None,
            message: "duplicate".to_owned(),
            severity: DiagnosticSeverity::ERROR,
        };
        assert_eq!(precision_of(&located), Precision::Form);
    }

    #[test]
    fn precision_file_when_neither_is_set() {
        let located = Located {
            code: None,
            identity: None,
            position: None,
            message: "malformed".to_owned(),
            severity: DiagnosticSeverity::ERROR,
        };
        assert_eq!(precision_of(&located), Precision::File);
    }

    #[test]
    fn token_span_at_expands_to_the_enclosing_word() {
        let text = "(rule bogus-token)";
        let (start, end) = token_span_at(text, 8); // inside "bogus-token"
        assert_eq!(&text[start..end], "bogus-token");
    }

    #[test]
    fn token_span_at_a_delimiter_is_one_byte() {
        let text = "(rule)";
        let (start, end) = token_span_at(text, 0); // the '(' itself
        assert_eq!(&text[start..end], "(");
    }

    #[test]
    fn a_real_lexical_error_position_locates_the_offending_token() {
        // `~=` is not a valid comparison operator — `ReadErrorKind::Lex
        // (LexCode::UnclassifiableToken)`, `E-LEX-003`, the same vector
        // `conformance_corpus.rs`'s own correction-3 test uses.
        let err = read("(~= agitation 0.5p)").expect_err("must be a read error");
        let located = Located {
            code: Some(match &err.kind {
                babylon_bsl::ReadErrorKind::Lex(code) => code.spec_code(),
                _ => unreachable!("this fixture is a lex error"),
            }),
            identity: None,
            position: Some(err.position),
            message: err.message.clone(),
            severity: DiagnosticSeverity::ERROR,
        };
        assert_eq!(precision_of(&located), Precision::Exact);
        let (start, end) = token_span_at("(~= agitation 0.5p)", located.position.unwrap());
        assert_eq!(&"(~= agitation 0.5p)"[start..end], "~=");
    }

    #[test]
    fn missing_manifest_row_is_information_severity_file_level_no_code() {
        let text = "(rule x (bindings) (effects))";
        let line_index = LineIndex::new(text);
        let d = missing_manifest_row_diagnostic(text, &line_index, "orphan.bsl");
        assert_eq!(d.severity, Some(DiagnosticSeverity::INFORMATION));
        assert_eq!(d.code, None);
        assert!(d.message.contains("orphan.bsl"));
        assert_eq!(d.range.start.line, 0);
    }

    #[test]
    fn diagnostics_for_file_sorts_into_the_declared_total_order() {
        let text = "(intrinsic floor :params (real) :returns int :cost 5) \
                    (intrinsic floor :params (real) :returns int :cost 6) \
                    (rule event/probe :material-basis \"x\" :fuel 16 (bindings) (effects (emit EventType/CONSCIOUSNESS_SHIFT (gate 0))))";
        let line_index = LineIndex::new(text);
        let located = vec![
            Located {
                code: Some("E-LOAD-001"),
                identity: Some(ErrorIdentity::Name("floor".to_owned())),
                position: None,
                message: "duplicate intrinsic".to_owned(),
                severity: DiagnosticSeverity::ERROR,
            },
            Located {
                code: None,
                identity: None,
                position: None,
                message: "aaa file-level comes first alphabetically among equal ranges".to_owned(),
                severity: DiagnosticSeverity::ERROR,
            },
        ];
        let diags = diagnostics_for_file(&uri(), text, &line_index, &located);
        assert_eq!(diags.len(), 2);
        // Both fall back to file-level (ambiguous "floor" + File-tier
        // prose) — the SAME range — so the total order's `message`
        // tiebreak decides, and "aaa..." < "duplicate intrinsic".
        assert!(diags[0].message.starts_with("aaa"));
    }

    #[test]
    fn duplicate_intrinsic_locates_ambiguous_with_two_related_information_entries() {
        let text = "(intrinsic floor :params (real) :returns int :cost 5) \
                    (intrinsic floor :params (real) :returns int :cost 6) \
                    (rule event/probe :material-basis \"x\" :fuel 16 (bindings) (effects (emit EventType/CONSCIOUSNESS_SHIFT (gate 0))))";
        let line_index = LineIndex::new(text);
        let load_err = LoadError::Intrinsic(babylon_bsl::DeclError::Duplicate {
            name: "floor".to_owned(),
            what: "intrinsic",
        });
        let located = Located::from_load_error(&load_err);
        assert_eq!(located.code, Some("E-LOAD-001"));
        let diags = diagnostics_for_file(&uri(), text, &line_index, std::slice::from_ref(&located));
        assert_eq!(diags.len(), 1);
        let related = diags[0]
            .related_information
            .as_ref()
            .expect("ambiguous outcome carries relatedInformation");
        assert_eq!(related.len(), 2);
        // "the second declaration": relatedInformation[1] is the later
        // (higher-offset) `floor` occurrence, sorted into document order.
        assert!(
            related[0].location.range.start.character < related[1].location.range.start.character
        );
    }

    #[test]
    fn compute_result_id_is_deterministic_and_order_sensitive() {
        let uri_a = Url::parse("file:///a.bsl").unwrap();
        let uri_b = Url::parse("file:///b.bsl").unwrap();
        let manifest = b"schema = 1";
        let ab = compute_result_id(&[(&uri_a, b"one"), (&uri_b, b"two")], manifest);
        let ab_again = compute_result_id(&[(&uri_a, b"one"), (&uri_b, b"two")], manifest);
        let ba = compute_result_id(&[(&uri_b, b"two"), (&uri_a, b"one")], manifest);
        assert_eq!(ab, ab_again);
        assert_ne!(ab, ba, "entry order is part of the hashed contract");
    }
}
