//! The per-file diagnostic pass (issue #652 Task 6, plan §6.3): resolve a
//! `.bsl` path to its content set(s) via the [`ContentSetManifest`], run
//! `babylon-tick`'s `diagnose_content_set`, and map every resulting error
//! to a [`lsp_types::Diagnostic`] located within THIS file's own forest.
//! Sits above [`crate::diagnostics`] (the mapping layer) and
//! [`crate::locator`]; [`crate::lifecycle`]'s push/pull wiring calls in
//! here, never into the mapping layer directly.
//!
//! **`SourceReader`** is the seam between "how a file's text is obtained"
//! and "what to do with it": a real server reads open documents from its
//! [`crate::document_store::DocumentStore`] and everything else from disk
//! (`DiskSourceReader`); a test injects fixtures in memory
//! (`FixtureSourceReader`) with no filesystem at all.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use lsp_types::{Diagnostic, Url};

use babylon_tick::diagnose_content_set;

use crate::content_manifest::ContentSetManifest;
use crate::diagnostics::{diagnostics_for_file, missing_manifest_row_diagnostic, Located};
use crate::document_store::DocumentStore;
use crate::line_index::LineIndex;

/// Obtain a content-root-relative file's current text — open-document
/// content when open, disk content otherwise (§6.1: "on-disk edits
/// outside open documents are picked up... at pull time").
pub trait SourceReader {
    /// `None` when the path names no readable source at all (never a
    /// panic — a sibling file a set names but that is missing on disk is
    /// a REAL condition, not a bug in this crate).
    fn read(&self, content_relative_path: &str) -> Option<String>;
}

/// Reads every path straight from disk, rooted at `content_root` (the
/// manifest's own directory, §4.1's "relative to THIS FILE's directory").
pub struct DiskSourceReader<'a> {
    /// The content root every manifest path is relative to.
    pub content_root: &'a Path,
}

impl SourceReader for DiskSourceReader<'_> {
    fn read(&self, content_relative_path: &str) -> Option<String> {
        std::fs::read_to_string(self.content_root.join(content_relative_path)).ok()
    }
}

/// The real server's own reader (§6.1: "on-disk edits outside open
/// documents are picked up only at pull time"): an open document's
/// current buffer wins over its on-disk content; anything not open reads
/// straight from disk under `content_root`.
pub struct LiveSourceReader<'a> {
    /// The content root every manifest path is relative to.
    pub content_root: &'a Path,
    /// The in-memory document store — checked first.
    pub store: &'a DocumentStore,
}

impl SourceReader for LiveSourceReader<'_> {
    fn read(&self, content_relative_path: &str) -> Option<String> {
        let absolute = self.content_root.join(content_relative_path);
        if let Ok(uri) = Url::from_file_path(&absolute) {
            if let Some(document) = self.store.get(&uri) {
                return Some(document.text.clone());
            }
        }
        std::fs::read_to_string(&absolute).ok()
    }
}

/// An in-memory fixture reader — no filesystem, deterministic, for tests.
#[derive(Debug, Default, Clone)]
pub struct FixtureSourceReader {
    /// Content-root-relative path → source text.
    pub files: HashMap<String, String>,
}

impl SourceReader for FixtureSourceReader {
    fn read(&self, content_relative_path: &str) -> Option<String> {
        self.files.get(content_relative_path).cloned()
    }
}

/// Diagnose one `.bsl` file (§6.3's own bullet): resolve its content
/// set(s) from `manifest`, run [`diagnose_content_set`] against each, and
/// map every resulting `PrepareError` to a `Diagnostic` located in THIS
/// file's own `(forest, SpanTable)`. A path naming no manifest row at all
/// gets exactly the Information notice (§6.3's own "declaration-
/// independent stages" bullet is Task 6's own File-tier default: a file
/// this crate cannot resolve to a content set gets no partial re-run of
/// the pipeline against a fabricated context, only the drift alarm).
///
/// Bounded by `sets.len()` (Power-of-10 rule 2) — a file named by more
/// than one set (`carceral-arc-conformance.bscn`'s two rule packs, §4.2)
/// gets the union of every set's own diagnostics.
#[must_use]
pub fn diagnose_bsl(
    uri: &Url,
    content_relative_path: &str,
    manifest: &ContentSetManifest,
    source: &dyn SourceReader,
) -> Vec<Diagnostic> {
    let Some(text) = source.read(content_relative_path) else {
        return Vec::new();
    };
    let line_index = LineIndex::new(&text);
    let sets = manifest.sets_for(content_relative_path);
    if sets.is_empty() {
        return vec![missing_manifest_row_diagnostic(
            &text,
            &line_index,
            content_relative_path,
        )];
    }
    let mut located: Vec<Located> = Vec::new();
    for set in &sets {
        let Some(scenario_src) = source.read(&set.scenario) else {
            continue;
        };
        let prelude_src = set.prelude.first().and_then(|p| source.read(p));
        let rule_srcs: Vec<String> = set.rules.iter().filter_map(|r| source.read(r)).collect();
        let rule_refs: Vec<&str> = rule_srcs.iter().map(String::as_str).collect();
        let errors = diagnose_content_set(&scenario_src, prelude_src.as_deref(), &rule_refs);
        located.extend(errors.iter().map(Located::from_prepare_error));
    }
    diagnostics_for_file(uri, &text, &line_index, &located)
}

/// The manifest's own directory (§4.1: "Paths... are relative to THIS
/// FILE's directory") — the content root [`DiskSourceReader`] joins every
/// path against.
#[must_use]
pub fn content_root_of(manifest_path: &Path) -> PathBuf {
    manifest_path
        .parent()
        .map_or_else(|| PathBuf::from("."), Path::to_path_buf)
}

/// The content-root-relative path for `uri`, when it lies under
/// `content_root` — `None` for a file this content root does not own (a
/// legitimate case, not a bug: a workspace can hold files `bsl-ls` never
/// resolves to a content set at all).
#[must_use]
pub fn content_relative_path(content_root: &Path, uri: &Url) -> Option<String> {
    let absolute = uri.to_file_path().ok()?;
    let relative = absolute.strip_prefix(content_root).ok()?;
    // TOML paths use forward slashes (§4.1's own examples); this crate
    // only ever runs on Unix (the flake's own devshells), where `Path`'s
    // components already use them.
    Some(relative.to_string_lossy().into_owned())
}

#[cfg(test)]
mod tests {
    use super::{diagnose_bsl, FixtureSourceReader};
    use crate::content_manifest::ContentSetManifest;
    use lsp_types::Url;
    use std::path::Path;

    fn uri() -> Url {
        Url::parse("file:///rules/probe.bsl").expect("valid test URI")
    }

    const SCENARIO: &str = "(scenario ft/probe)";
    // "vitality" is one of `babylon-tick`'s own registered namespaces
    // (`registered_systems`) — unlike "event" (a babylon-bsl conformance-
    // corpus-only namespace), a rule anchored under it clears the §2.3
    // anchor default check that `diagnose_content_set` actually runs.
    const RULE: &str = "(rule vitality/probe :role mechanic :evidence derived :material-basis \"x\" :fuel 16 (bindings) \
                         (effects (emit EventType/CONSCIOUSNESS_SHIFT (gate 0))))";

    fn manifest_with_one_set() -> ContentSetManifest {
        let toml = r#"
schema = 1
[[set]]
id = "probe/set"
scenario = "scenario.bscn"
prelude = []
rules = ["rules/probe.bsl"]
consumers = []
note = "test fixture"
"#;
        ContentSetManifest::parse(Path::new("content-sets.toml"), toml).expect("valid manifest")
    }

    #[test]
    fn a_clean_content_set_produces_no_diagnostics() {
        let manifest = manifest_with_one_set();
        let source = FixtureSourceReader {
            files: [
                ("scenario.bscn".to_owned(), SCENARIO.to_owned()),
                ("rules/probe.bsl".to_owned(), RULE.to_owned()),
            ]
            .into_iter()
            .collect(),
        };
        let diags = diagnose_bsl(&uri(), "rules/probe.bsl", &manifest, &source);
        assert!(diags.is_empty(), "{diags:?}");
    }

    #[test]
    fn a_path_with_no_manifest_row_gets_the_information_notice() {
        let manifest = manifest_with_one_set();
        let source = FixtureSourceReader {
            files: [("orphan.bsl".to_owned(), RULE.to_owned())]
                .into_iter()
                .collect(),
        };
        let diags = diagnose_bsl(&uri(), "orphan.bsl", &manifest, &source);
        assert_eq!(diags.len(), 1);
        assert_eq!(
            diags[0].severity,
            Some(lsp_types::DiagnosticSeverity::INFORMATION)
        );
        assert!(diags[0].message.contains("orphan.bsl"));
    }

    #[test]
    fn diagnosing_the_same_content_set_twice_is_byte_identical() {
        let manifest = manifest_with_one_set();
        let source = FixtureSourceReader {
            files: [
                ("scenario.bscn".to_owned(), SCENARIO.to_owned()),
                (
                    "rules/probe.bsl".to_owned(),
                    "(intrinsic floor :params (real) :returns int :cost 5) \
                     (intrinsic floor :params (real) :returns int :cost 6) "
                        .to_owned()
                        + RULE,
                ),
            ]
            .into_iter()
            .collect(),
        };
        let first = diagnose_bsl(&uri(), "rules/probe.bsl", &manifest, &source);
        let second = diagnose_bsl(&uri(), "rules/probe.bsl", &manifest, &source);
        assert_eq!(
            serde_json::to_string(&first).unwrap(),
            serde_json::to_string(&second).unwrap()
        );
        assert!(!first.is_empty());
    }
}
