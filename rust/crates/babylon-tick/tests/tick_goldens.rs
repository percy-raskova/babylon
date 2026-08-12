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
const ORG_FOUNDATION_SCENARIO: &str =
    include_str!("../content/scenarios/organization-foundation.bscn");
const ORG_FOUNDATION_RULE: &str = include_str!("../content/rules/organization.bsl");
const TERRITORY_SCENARIO: &str = include_str!("../content/scenarios/territory-conformance.bscn");
const TERRITORY_RULE: &str = include_str!("../content/rules/territory.bsl");
const PRODUCTION_SCENARIO: &str = include_str!("../content/scenarios/production-conformance.bscn");
const PRODUCTION_RULE: &str = include_str!("../content/rules/production.bsl");

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

/// Task 10 (Organization foundation plan) — spec §11's hash anchor: the
/// org-seeding canonical scenario, pinned. `organization-foundation.bscn`
/// declares NodeType/EdgeType vocabularies plus the `OrgKind` enum
/// (ADR195/ADR196), seeds two organizations (a CIVIL_SOCIETY reading group
/// and a STATE_APPARATUS precinct) over a class and a territory, and the
/// `organization/kind-probe` rule reads `organization/kind` back through a
/// `:field` binding (`field-of` is refused for enum-declared fields — D102)
/// to fire on the one STATE_APPARATUS organization only.
///
/// `before == after` here is not a bug: the probe rule's only effect is
/// `emit` — no `update-node` — and the tick-hash contract
/// (`babylon-graph/src/state_hash.rs`, §"The canonical byte layout") covers
/// only nodes/attributes/edges/hyperedges, never the event log. A rule that
/// observes but does not mutate leaves the graph, and therefore the hash,
/// genuinely unmoved; measured, not assumed. The `before` pin still
/// discriminates — a reordered `defenum` moves it (declaration order IS the
/// stored ordinal, ADR195) — and `fired == 1` pins both halves of the
/// guard. What NO golden can pin today is the emit itself (`TickReport`
/// carries no event log); that blind spot closes at the Events-in-BSL
/// workstream's observable seam (WS1, #502), not by rewriting this probe.
#[test]
fn organization_foundation_hashes_are_pinned() {
    let report = run_once(ORG_FOUNDATION_SCENARIO, ORG_FOUNDATION_RULE)
        .expect("organization-foundation tick");
    assert_eq!(
        hex(&report.before),
        "5d8d5c43088440787f993ce91bd9a676d4adf60fa35904b2afbafeccaab93a1e",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         organization-foundation.bscn (the org estate's first entry into \
         the Rust byte gate, spec §11)"
    );
    assert_eq!(
        hex(&report.after),
        "5d8d5c43088440787f993ce91bd9a676d4adf60fa35904b2afbafeccaab93a1e",
        "post-tick hash moved — the probe rule's own effect is emit-only \
         (no update-node), so this staying equal to `before` is the \
         expected, measured result, not an oversight; a future rule that \
         adds a mutating effect to this pack SHOULD move this value"
    );
    assert_eq!(
        report.fired, 1,
        "the probe rule must fire for exactly the one STATE_APPARATUS \
         organization (precinct) and skip the CIVIL_SOCIETY one \
         (reading-group)"
    );
}

/// The Territory port's own composition golden (P27 PR B, Task 8): all
/// FIVE `territory/*` rules against the twelve-territory/three-class
/// conformance world in one tick — the port train's entry into the Rust
/// byte gate. `territory_conformance.rs`'s own suite already pins every
/// STRUCTURAL claim this hash summarizes (the latch set, the sink
/// tiebreak, the suppression set, the camp's same-tick decay); this
/// golden exists to catch ANY unintentional drift a structural assertion
/// happens not to cover — the same class of blind spot
/// `us_counties_lifecycle_demo_hashes_are_pinned`'s own header names.
#[test]
fn territory_conformance_hashes_are_pinned() {
    // Re-pinned once (fix round, 2026-08-12) after the fixture-change batch
    // (MINOR-4: sink-reservation seeded nonzero; MINOR-7: the D123
    // directed-walk witness edge; NIT-10: sink-reservation declared before
    // sink-penal) — this golden is new in this PR, so the re-pin is a
    // measurement, not a ceremony (III.13 baseline ceremonies apply to
    // `tests/baselines/**`, not this crate's own goldens).
    let report = run_once(TERRITORY_SCENARIO, TERRITORY_RULE).expect("territory tick");
    assert_eq!(
        hex(&report.before),
        "3794b114d302a8466889795573ecf3f87547af5c200e1ead11c4fc9fcac88ad6",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         territory-conformance.bscn (twelve territories + three social \
         classes + eight edges)"
    );
    assert_eq!(
        hex(&report.after),
        "510091298354429a755e6b851c9db356b2b1d7c35e74d092447535a7883e1af8",
        "post-tick hash moved — all five phase rules' combined tick-1 output"
    );
    assert_eq!(
        report.fired, 30,
        "12 (p1) + 4 (p2) + 12 (p3) + 1 (p4-camp-decay) + 1 (p4-penal-suppression) = 30"
    );
}

/// The Production port's own composition golden (P27, issue #565, Task 5):
/// all FOUR `production/*` rules against the eight-social-class/four-
/// territory conformance world in one tick — the port train's entry into
/// the Rust byte gate. `production_conformance.rs`'s own suite already pins
/// every STRUCTURAL claim this hash summarizes (the wealth ledger, the
/// employer accumulation, the idle-worker hash-neutral vector, the
/// extraction-intensity broadcast including its own genuine multi-tenancy
/// divergence from the frozen mirror); this golden exists to catch ANY
/// unintentional drift a structural assertion happens not to cover — the
/// same class of blind spot `territory_conformance_hashes_are_pinned`'s own
/// header names. This is a PURE ADDITION: the five pre-existing pins above
/// are untouched by this content pair's own load/rules.
#[test]
fn production_conformance_hashes_are_pinned() {
    let report = run_once(PRODUCTION_SCENARIO, PRODUCTION_RULE).expect("production tick");
    assert_eq!(
        hex(&report.before),
        "e9cbc3cf10b878fb4e1f3396144407142c748b15178b1e8c5a719925cfed529e",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         production-conformance.bscn (eight social classes + four \
         territories + eleven edges)"
    );
    assert_eq!(
        hex(&report.after),
        "25308d98a3a8c5c6bd6113c3cf7c27eda3c13ba909246319cf15319a946daa0a",
        "post-tick hash moved — all four rules' combined tick-1 output"
    );
    assert_eq!(
        report.fired, 10,
        "2 (p1) + 3 (p2) + 1 (p3) + 4 (p4) = 10 — the plan's own predicted arithmetic, \
         verified rather than trusted"
    );
}
