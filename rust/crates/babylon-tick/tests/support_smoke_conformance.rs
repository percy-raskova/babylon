//! Compile-time proof that the whole `support` API — [`support::attribute`],
//! [`support::run_conformance`], [`support::ExpectedField`],
//! [`support::assert_expected`], and [`support::assert_deterministic`] — is
//! real and usable together (R2.1.1's RED artifact,
//! `docs/superpowers/plans/2026-08-18-bsl-refactor-program.md` §4 Task
//! R2.1). Reuses the existing `metabolism-entropy-high-conformance.bscn` +
//! `metabolism.bsl` fixture pair and its already-verified values
//! (`metabolism_entropy_high_conformance.rs`'s own docstring, re-proved
//! here through the new shared module rather than fabricated as new data).
//!
//! RED (this commit): fails to compile — `tests/support/mod.rs` does not
//! exist yet.

mod support;

use babylon_graph::memory::MemoryGraph;
use support::{assert_deterministic, assert_expected, attribute, run_conformance, ExpectedField};

const SCENARIO: &str =
    include_str!("../content/scenarios/metabolism-entropy-high-conformance.bscn");
const RULE: &str = include_str!("../content/rules/metabolism.bsl");

const EXPECTED: [ExpectedField; 2] = [
    ExpectedField {
        name: "high-entropy-county",
        id: 0,
        field: "territory/biocapacity",
        value: 0.0,
    },
    ExpectedField {
        name: "high-entropy-county",
        id: 0,
        field: "territory/max-biocapacity",
        value: 99.95,
    },
];

/// Exercises `run_conformance` (the plain-`G` `run_*` shape) and
/// `ExpectedField`/`assert_expected` (the generic pin table) together, and
/// `attribute` directly as a sanity cross-check against the same read.
#[test]
fn the_shared_harness_reproduces_the_high_entropy_fixture_exactly() {
    let graph: MemoryGraph = run_conformance(SCENARIO, RULE);
    assert_expected(&graph, &EXPECTED);
    assert_eq!(attribute(&graph, 0u64, "territory/biocapacity"), 0.0);
}

/// Exercises `assert_deterministic` — the double-run-compare-hash idiom.
#[test]
fn the_shared_harness_double_run_hash_matches() {
    let report = assert_deterministic(SCENARIO, RULE);
    assert_eq!(report.fired, 1);
}
