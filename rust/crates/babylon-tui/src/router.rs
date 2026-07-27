//! Parser for `babylon://` navigation URIs.
//!
//! Ports `babylon.tui.router` (Python) semantics exactly. The wikilink render
//! rule emits two href shapes:
//!
//! * `babylon://<target>` — a known entity, addressed bare (no kind segment).
//! * `babylon://redlink/<target>` — an unresolved target.
//!
//! Other Archive UI (statblocks, the command palette, future explicit-kind
//! links) may address entities with an explicit kind segment:
//! `babylon://<kind>/<id>`. This module parses all three shapes into one
//! [`BabylonTarget`]; anything else is a [`RouterError`] (Constitution
//! III.11 — no silent best-effort parsing of a malformed URI).

use thiserror::Error;

/// The `babylon://` URI scheme.
pub const SCHEME: &str = "babylon";

/// The netloc value that marks an unresolved (redlink) target.
pub const REDLINK_KIND: &str = "redlink";

/// Kind sentinel assigned to bare `babylon://<id>` hrefs (no explicit kind
/// segment) — ports the Python module's `BARE_KIND`. Python's
/// `format_babylon_uri` emits the bare form THROUGH this sentinel
/// (`babylon://wikilink/<id>`), so both spellings parse to
/// [`BabylonTarget::Entity`] for cross-implementation round-trips.
pub const BARE_KIND: &str = "wikilink";

/// A parsed `babylon://` navigation target.
///
/// * [`BabylonTarget::Entity`] — a bare `babylon://<id>` href (no explicit
///   kind segment; corresponds to the Python module's `kind="wikilink"`).
/// * [`BabylonTarget::Kind`] — an explicit-kind `babylon://<kind>/<id>` href.
/// * [`BabylonTarget::Redlink`] — an unresolved `babylon://redlink/<id>` href.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BabylonTarget {
    /// A bare `babylon://<id>` href; the payload is the raw identifier
    /// segment (the Python module's `entity_id` with `kind="wikilink"`).
    Entity(String),
    /// An explicit-kind `babylon://<kind>/<id>` href.
    Kind {
        /// The entity kind (e.g. `"county"`).
        kind: String,
        /// The raw identifier segment (may itself contain `/`).
        id: String,
    },
    /// An unresolved `babylon://redlink/<id>` href; the payload is the raw
    /// target (may itself contain `/`, e.g. `"org/uaw-9999"`).
    Redlink(String),
}

/// Errors raised when parsing a malformed `babylon://` URI.
///
/// Mirrors the four failure modes of the Python module's
/// `InvalidBabylonUri`, split into distinct variants for programmatic
/// matching; the `Display` text preserves the Python messages' key phrases
/// (`"not a babylon"`, `"missing host"`, `"malformed"`) so callers porting
/// Python's `pytest.raises(..., match=...)` assertions have a direct analog.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum RouterError {
    /// The URI scheme was not `babylon://` (includes the empty string, which
    /// has no scheme at all).
    #[error("not a babylon:// uri: {0:?}")]
    NotBabylonScheme(String),
    /// The URI had no host/kind segment (e.g. `babylon:///26163`).
    #[error("missing host/kind segment: {0:?}")]
    MissingHost(String),
    /// The host/kind segment failed the kind character class.
    #[error("malformed kind/id segment: {0:?}")]
    MalformedKind(String),
    /// The path segment failed the entity-id character class.
    #[error("malformed entity id: {0:?}")]
    MalformedEntityId(String),
}

/// A kind segment, or a bare (no-path) target: a single path token, no `/`.
///
/// Ports the Python module's `_KIND_RE = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"`.
fn is_valid_kind(s: &str) -> bool {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) if c.is_ascii_alphanumeric() => {}
        _ => return false,
    }
    chars.all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '_' || c == '-')
}

/// An entity id following an explicit kind: may itself be `/`-shaped (e.g.
/// wikilink targets conventionally look like `county/26163`).
///
/// Ports the Python module's `_ENTITY_ID_RE = r"^[A-Za-z0-9][A-Za-z0-9._/-]*$"`.
fn is_valid_entity_id(s: &str) -> bool {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) if c.is_ascii_alphanumeric() => {}
        _ => return false,
    }
    chars.all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '_' || c == '/' || c == '-')
}

/// Splits a URI into `(scheme, netloc, path)`, mirroring the subset of
/// Python's `urllib.parse.urlsplit` behavior this module depends on: a
/// `scheme://netloc/path` shape, where `netloc` is everything up to the next
/// `/`, `?`, or `#` (or end of string). Not a general URI parser — this is
/// the same narrow slice of `urlsplit` semantics `router.py` itself relies on.
fn split_uri(uri: &str) -> (String, String, String) {
    if let Some(idx) = uri.find("://") {
        let scheme = uri[..idx].to_string();
        let rest = &uri[idx + 3..];
        let end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
        let netloc = rest[..end].to_string();
        let path = rest[end..].to_string();
        (scheme, netloc, path)
    } else if let Some(idx) = uri.find(':') {
        let scheme = uri[..idx].to_string();
        let path = uri[idx + 1..].to_string();
        (scheme, String::new(), path)
    } else {
        (String::new(), String::new(), uri.to_string())
    }
}

/// Parses a `babylon://` URI into a [`BabylonTarget`].
///
/// Accepted shapes:
///
/// * `babylon://<id>` — bare form; [`BabylonTarget::Entity`].
/// * `babylon://redlink/<id>` — [`BabylonTarget::Redlink`].
/// * `babylon://<kind>/<id>` — explicit kind; [`BabylonTarget::Kind`].
///
/// # Errors
///
/// Returns [`RouterError`] if the scheme is wrong, a required segment is
/// missing, or a segment fails the entity-id character class.
pub fn parse_babylon_uri(uri: &str) -> Result<BabylonTarget, RouterError> {
    let (scheme, netloc, path_raw) = split_uri(uri);
    if scheme != SCHEME {
        return Err(RouterError::NotBabylonScheme(uri.to_string()));
    }
    let path = path_raw.trim_start_matches('/');

    if netloc.is_empty() {
        return Err(RouterError::MissingHost(uri.to_string()));
    }
    if !is_valid_kind(&netloc) {
        return Err(RouterError::MalformedKind(uri.to_string()));
    }

    if path.is_empty() {
        // Bare form: babylon://<id> — netloc IS the id, kind defaults.
        return Ok(BabylonTarget::Entity(netloc));
    }

    if !is_valid_entity_id(path) {
        return Err(RouterError::MalformedEntityId(uri.to_string()));
    }

    if netloc == REDLINK_KIND {
        Ok(BabylonTarget::Redlink(path.to_string()))
    } else if netloc == BARE_KIND {
        // babylon://wikilink/<id> — the sentinel-prefixed bare form Python's
        // format_babylon_uri emits; same target as bare babylon://<id>.
        Ok(BabylonTarget::Entity(path.to_string()))
    } else {
        Ok(BabylonTarget::Kind {
            kind: netloc,
            id: path.to_string(),
        })
    }
}

/// Renders a [`BabylonTarget`] back to its `babylon://` URI form.
///
/// Round-trips with [`parse_babylon_uri`]:
/// `parse_babylon_uri(&format_babylon_uri(&t)) == Ok(t)` for any `t` produced
/// by that function. Ports the Python module's `format_babylon_uri`.
pub fn format_babylon_uri(target: &BabylonTarget) -> String {
    match target {
        // Python parity: the bare form formats THROUGH the BARE_KIND
        // sentinel (`prefix = target.kind` where the bare kind IS
        // "wikilink"), never as `babylon://<id>` — a bare id could
        // otherwise collide with a kind segment on re-parse.
        BabylonTarget::Entity(id) => format!("{SCHEME}://{BARE_KIND}/{id}"),
        BabylonTarget::Kind { kind, id } => format!("{SCHEME}://{kind}/{id}"),
        BabylonTarget::Redlink(id) => format!("{SCHEME}://{REDLINK_KIND}/{id}"),
    }
}
