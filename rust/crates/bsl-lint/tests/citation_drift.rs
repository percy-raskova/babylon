//! Integration tests for `bsl-lint citation-drift` (task brief W1.1/W1.3).
//! Spawns the compiled binary against `tests/fixtures/rules/stale_citation.bsl`
//! — every citation in that fixture targets the REAL frozen
//! `src/babylon/engine/systems/solidarity.py` at the `p27-python-freeze`
//! tag (202 lines), so these tests exercise the real git-tag resolution
//! path, not a stand-in.

use std::path::PathBuf;
use std::process::Command;

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/rules/stale_citation.bsl")
}

fn run_citation_drift() -> (i32, String) {
    let output = Command::new(env!("CARGO_BIN_EXE_bsl-lint"))
        .arg("citation-drift")
        .arg(fixture_path())
        .output()
        .expect("bsl-lint must run");
    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
    (output.status.code().unwrap_or(-1), stdout)
}

#[test]
fn a_span_beyond_the_frozen_files_line_count_fails() {
    let (code, stdout) = run_citation_drift();
    assert_eq!(code, 1, "stdout was:\n{stdout}");
    assert!(
        stdout.contains("E-SENTINEL citation-drift")
            && stdout.contains("out of bounds")
            && stdout.contains("solidarity.py:97-999"),
        "expected an out-of-bounds FAIL line, got:\n{stdout}"
    );
}

#[test]
fn an_in_bounds_span_with_no_nearby_keyword_warns_not_fails() {
    let (_, stdout) = run_citation_drift();
    let warn_line = stdout
        .lines()
        .find(|l| l.contains("solidarity.py:1-3"))
        .unwrap_or_else(|| panic!("expected a solidarity.py:1-3 line, got:\n{stdout}"));
    assert!(
        warn_line.starts_with("W-SENTINEL"),
        "keyword-miss must WARN, not FAIL: {warn_line}"
    );
    assert!(warn_line.contains("no keyword nearby"), "{warn_line}");
}

#[test]
fn a_grounded_in_bounds_citation_with_a_nearby_keyword_is_clean() {
    let (_, stdout) = run_citation_drift();
    assert!(
        !stdout.contains("solidarity.py:1-14"),
        "the clean citation must produce no finding at all:\n{stdout}"
    );
}

#[test]
fn list_includes_citation_drift() {
    let output = Command::new(env!("CARGO_BIN_EXE_bsl-lint"))
        .arg("--list")
        .output()
        .expect("bsl-lint --list must run");
    assert_eq!(output.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("citation-drift"));
    assert!(stdout.contains("namespace-unique"));
}
