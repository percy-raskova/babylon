//! Widens the tick-hash golden surface from ONE pinned end-to-end hash
//! (`babylon-client/tests/engine_link.rs`'s post-tick hash on
//! two-classes.bscn + fundamental-theorem.bsl) to SIX: pre- and post-tick,
//! on all THREE committed content pairs `babylon-tick`/`babylon-client`
//! ship (two single-rule pairs plus the B2 demo world's two-rule pair).
//! The pre-tick value for the first pair previously appeared only in prose
//! (`docs/superpowers/plans/2026-08-11-hypergraph-storage-swap-plan.md`
//! Task 3); this is where it becomes an executable pin.
//!
//! This surface exists to catch the storage swap — or, for the third pair,
//! ANY unintentional drift in the shipped demo content or the two rule
//! packs it composes — moving a byte the single `engine_link` pin would
//! miss. A change that happened to leave the FINAL hash of ONE content
//! pair unmoved by coincidence would still move at least one of these six.
//! Mutation-proven (adversarial-panel finding FB4, this fix round):
//! tripling `us-counties-lifecycle-demo.bscn`'s county-01011 `pop-d`, and
//! a total-preserving recomposition of county-01001's `pop-d`/`pop-p`
//! (2042/5748 -> 2043/5747), both left every OTHER test in this crate and
//! `babylon-client` green — this golden is what catches either.
//!
//! Measured, never derived: every hash below was produced by running
//! `run_once` once against the committed content and reading the printed
//! value back — see the storage-swap plan, Phase A Task 3, Step 1, for the
//! first two pairs; the third pair's hashes were measured the same way at
//! this fix round's own tip (2026-08-11) and cross-confirmed against the
//! identical post-tick hash `tests/tick_loop.rs`'s own
//! `pressing_space_advances_the_tick_and_updates_the_hash_text` observes
//! through the client's independent `EngineSession` seam.

use babylon_tick::{hex, run_once};

const TWO_CLASSES_SCENARIO: &str = include_str!("../content/scenarios/two-classes.bscn");
const FUNDAMENTAL_THEOREM_RULE: &str = include_str!("../content/rules/fundamental-theorem.bsl");
const VITALITY_SCENARIO: &str = include_str!("../content/scenarios/vitality-conformance.bscn");
const VITALITY_RULE: &str = include_str!("../content/rules/vitality.bsl");
const DEMO_SCENARIO: &str = include_str!("../content/scenarios/us-counties-lifecycle-demo.bscn");
const DEMO_VITALITY_RULE: &str = include_str!("../content/rules/vitality.bsl");
const DEMO_LIFECYCLE_RULE: &str = include_str!("../content/rules/lifecycle.bsl");

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

/// The B2 demo world's own golden (adversarial-panel fix FB4): before this
/// test existed, NOTHING pinned `us-counties-lifecycle-demo.bscn`'s content
/// against silent drift — tripling county-01011's `pop-d`, or a
/// total-preserving recomposition of county-01001's `pop-d`/`pop-p`, both
/// left every other test in this crate and `babylon-client` green
/// (mutation-proven, this fix round). `run_once` composes the two rule
/// packs the same way `EngineSession::start`/`us_counties_demo.rs` do —
/// concatenation order is arbitrary (`prepare_rules` sorts by rule-id byte
/// order, §4.2/D16, regardless of it) — and runs tick 1.
#[test]
fn us_counties_lifecycle_demo_hashes_are_pinned() {
    let rule_src = format!("{DEMO_VITALITY_RULE}\n{DEMO_LIFECYCLE_RULE}");
    let report = run_once(DEMO_SCENARIO, &rule_src).expect("demo tick");
    assert_eq!(
        hex(&report.before),
        "c190053e6d5d6eb261f1325bf87a6347dad8bb99f4e6fb7f2e297d355ccc28ab",
        "pre-tick hash moved — this is the SUBSTRATE'S load of us-counties-lifecycle-demo.bscn \
         (twelve territories + six social classes)"
    );
    assert_eq!(
        hex(&report.after),
        "f4ea98647520ca8e5b2b74e4970626a179236b48efde144c91850c52640f2b5d",
        "post-tick hash moved — both rule packs' combined tick-1 output. Cross-confirmed against \
         the identical value babylon-client's EngineSession seam produces \
         (tests/tick_loop.rs::pressing_space_advances_the_tick_and_updates_the_hash_text)"
    );
}
