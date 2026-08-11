//! Widens the tick-hash golden surface from ONE pinned end-to-end hash
//! (`babylon-client/tests/engine_link.rs`'s post-tick hash on
//! two-classes.bscn + fundamental-theorem.bsl) to FOUR: pre- and post-tick,
//! on both committed content pairs `babylon-tick` ships. The pre-tick value
//! for the first pair previously appeared only in prose
//! (`docs/superpowers/plans/2026-08-11-hypergraph-storage-swap-plan.md`
//! Task 3); this is where it becomes an executable pin.
//!
//! This surface exists to catch the storage swap moving a byte the
//! single `engine_link` pin would miss — a change that happened to leave
//! the FINAL hash of ONE content pair unmoved by coincidence would still
//! move at least one of these four.
//!
//! Measured, never derived: every hash below was produced by running
//! `run_once` once against the committed content and reading the printed
//! value back — see the storage-swap plan, Phase A Task 3, Step 1.

use babylon_tick::{hex, run_once};

const TWO_CLASSES_SCENARIO: &str = include_str!("../content/scenarios/two-classes.bscn");
const FUNDAMENTAL_THEOREM_RULE: &str = include_str!("../content/rules/fundamental-theorem.bsl");
const VITALITY_SCENARIO: &str = include_str!("../content/scenarios/vitality-conformance.bscn");
const VITALITY_RULE: &str = include_str!("../content/rules/vitality.bsl");

#[test]
fn two_classes_fundamental_theorem_hashes_are_pinned() {
    let report =
        run_once(TWO_CLASSES_SCENARIO, FUNDAMENTAL_THEOREM_RULE).expect("two-classes tick");
    assert_eq!(
        hex(&report.before),
        "5a44ab0c426eca240a0010cc70321bd0ff944d2eee2408454899a942dc85a205",
        "pre-tick hash moved — this is the SUBSTRATE'S load of two-classes.bscn"
    );
    assert_eq!(
        hex(&report.after),
        "783f651d04d32fffd0109e88423eb7a57b1e0836ed4a9f645d3a8a554e427679",
        "post-tick hash moved — the same pin babylon-client's engine_link \
         asserts on this content pair"
    );
}

#[test]
fn vitality_conformance_hashes_are_pinned() {
    let report = run_once(VITALITY_SCENARIO, VITALITY_RULE).expect("vitality tick");
    assert_eq!(
        hex(&report.before),
        "20dbc24fc6ba17067cb26eb4ce4c2792c51cb0402395dc55363a5e4e38572fea",
        "pre-tick hash moved — this is the SUBSTRATE'S load of vitality-conformance.bscn"
    );
    assert_eq!(
        hex(&report.after),
        "4c7f95d967e2bf28cd5be91bbd439b61652d2c8d4103e8b5d7a3a8ad789baf64",
        "post-tick hash moved — the vitality pack's engine output"
    );
}
