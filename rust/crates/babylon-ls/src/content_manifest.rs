//! The content-set manifest reader (`content-sets.toml`, issue #652 Task 4,
//! plan §4) — schema-versioned TOML, one `[[set]]` row per co-loading unit.
//! **Named `content_manifest`, not `manifest`**, to stay clear of
//! `babylon_bsl::manifest`, which is a completely different thing: the
//! IN-LANGUAGE `(manifest …)` scenario form (`bsl-language.rst` §2.9).
//! Task 4 built the file; this module is its first Rust reader (§5.1: the
//! manifest is build metadata `bsl-ls` needs to resolve a `.bsl` file to
//! its content set, never content itself).
//!
//! **Read-only, observes-only (global constraint 1).** This module never
//! writes `content-sets.toml`; it is the DECLARATION (§4.3's own direction
//! note), and `bsl-ls` is one more reader alongside the Rust `include_str!`
//! call sites and the Python sync guard
//! (`tests/unit/reference/test_content_set_manifest_sync.py`).

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::Deserialize;

/// The whole manifest: `content-sets.toml`'s top-level shape (plan §4.1).
#[derive(Debug, Clone, Deserialize)]
pub struct ContentSetManifest {
    /// The manifest format version — read but not yet interpreted (wave 1
    /// has exactly one schema); a future incompatible change bumps this and
    /// gives a reader something to refuse against.
    pub schema: u32,
    /// One row per co-loading unit — `set` in the TOML, `sets` here (the
    /// plural Rust callers actually want).
    #[serde(rename = "set", default)]
    pub sets: Vec<ContentSet>,
    /// `.bsl`/`.bscn` paths that belong to no set yet, each with a reason
    /// (§4.1's own `[orphans]` table) — keyed by content-root-relative path.
    #[serde(default)]
    pub orphans: HashMap<String, String>,
}

/// One `[[set]]` row: a scenario (plus optional preludes) and the rule
/// sources that load against it as one unit.
#[derive(Debug, Clone, Deserialize)]
pub struct ContentSet {
    /// The set's id, e.g. `"control-ratio/conformance"`.
    pub id: String,
    /// The scenario path, relative to the manifest file's own directory
    /// (§4.1).
    pub scenario: String,
    /// Prelude paths, in load order, same relativity as `scenario`.
    #[serde(default)]
    pub prelude: Vec<String>,
    /// Rule-source paths — a SET, not a load order (§4.1's own comment: the
    /// loader sorts rule ids into ascending byte order before firing).
    pub rules: Vec<String>,
    /// Repo-relative paths of the Rust (or other) consumers that
    /// `include_str!` this row's files (D146).
    #[serde(default)]
    pub consumers: Vec<String>,
    /// Required by the sync guard (§4.3 row 3) when `consumers` is empty;
    /// not otherwise interpreted here.
    #[serde(default)]
    pub note: Option<String>,
}

/// A `content-sets.toml` read/parse failure.
#[derive(Debug)]
pub enum ContentManifestError {
    /// The file could not be read from disk.
    Io {
        /// The path that failed.
        path: PathBuf,
        /// The underlying I/O error, rendered (never carried as a raw
        /// `io::Error` — this type stays `PartialEq`-free-of-surprises and
        /// easy to assert on in tests).
        detail: String,
    },
    /// The file's contents are not valid TOML, or not this shape.
    Malformed {
        /// The path that failed.
        path: PathBuf,
        /// What `toml`'s own parser reported.
        detail: String,
    },
}

impl std::fmt::Display for ContentManifestError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io { path, detail } => {
                write!(f, "reading {}: {detail}", path.display())
            }
            Self::Malformed { path, detail } => {
                write!(
                    f,
                    "parsing {} as content-sets.toml: {detail}",
                    path.display()
                )
            }
        }
    }
}

impl std::error::Error for ContentManifestError {}

impl ContentSetManifest {
    /// Parse an already-read manifest source. The pure half of
    /// [`Self::load`] — the half a unit test exercises without touching a
    /// filesystem.
    ///
    /// # Errors
    ///
    /// [`ContentManifestError::Malformed`] when `text` is not valid
    /// `content-sets.toml`.
    pub fn parse(path: &Path, text: &str) -> Result<Self, ContentManifestError> {
        toml::from_str(text).map_err(|e| ContentManifestError::Malformed {
            path: path.to_path_buf(),
            detail: e.to_string(),
        })
    }

    /// Read and parse `path` (`content-sets.toml`'s own location).
    ///
    /// # Errors
    ///
    /// [`ContentManifestError::Io`] on a read failure,
    /// [`ContentManifestError::Malformed`] on a parse failure.
    pub fn load(path: &Path) -> Result<Self, ContentManifestError> {
        let text = std::fs::read_to_string(path).map_err(|e| ContentManifestError::Io {
            path: path.to_path_buf(),
            detail: e.to_string(),
        })?;
        Self::parse(path, &text)
    }

    /// Every `[[set]]` row whose `scenario`, any `prelude` entry, or any
    /// `rules` entry equals `content_relative_path` (a path relative to the
    /// manifest's own directory — the content root, §4.1). A `.bscn` used
    /// as a prelude by several sets, or a `.bsl` shared by several sets
    /// (`carceral-arc-conformance.bscn`'s two rule packs, §4.2), can match
    /// more than one row — bounded by `self.sets.len()` (Power-of-10 rule 2).
    #[must_use]
    pub fn sets_for(&self, content_relative_path: &str) -> Vec<&ContentSet> {
        self.sets
            .iter()
            .filter(|set| {
                set.scenario == content_relative_path
                    || set.prelude.iter().any(|p| p == content_relative_path)
                    || set.rules.iter().any(|r| r == content_relative_path)
            })
            .collect()
    }
}
