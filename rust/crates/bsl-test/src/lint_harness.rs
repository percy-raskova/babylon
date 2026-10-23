//! Lint harness over in-memory Rust fixtures.
//!
//! `bsl-lint`'s repo-relationship checks need a checkout; the AST style
//! sentinel is self-contained, so tests can run it on a string.

use bsl_lint::finding::Finding;
use bsl_lint::google_rust_style;
use std::path::Path;

const INLINE_FIXTURE: &str = "bsl-test-inline.rs";

/// Run the `google-rust-style` sentinel over one in-memory Rust source.
///
/// The synthetic path is a leaf module in no client crate, so the sentinel
/// applies its ordinary leaf-file rules.
///
/// # Errors
/// The path and parse failure when the source is not valid Rust.
pub fn run_bsl_check_on_str(source: &str) -> Result<Vec<Finding>, String> {
    google_rust_style::check_rust_source(Path::new(INLINE_FIXTURE), source)
}

/// Assert that one in-memory Rust source has no style findings.
///
/// # Panics
/// When the source is not valid Rust, or when the sentinel reports at least
/// one finding. The panic message lists every finding.
pub fn assert_bsl_lint_clean(source: &str) {
    let findings = match run_bsl_check_on_str(source) {
        Ok(findings) => findings,
        Err(error) => panic!("inline Rust fixture must parse before linting: {error}"),
    };
    assert!(
        findings.is_empty(),
        "inline Rust fixture must be style-clean; findings:\n{}",
        render(&findings)
    );
}

fn render(findings: &[Finding]) -> String {
    findings
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>()
        .join("\n")
}
