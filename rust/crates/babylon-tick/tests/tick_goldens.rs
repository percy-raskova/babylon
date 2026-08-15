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

use babylon_bsl::scenario::load_scenario;
use babylon_graph::hypergraph_store::HypergraphStore;
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
const WORLDVIEW_SCENARIO: &str = include_str!("../content/scenarios/worldview-foundation.bscn");
const WORLDVIEW_RULES: &str = include_str!("../content/rules/worldview.bsl");
const CONSCIOUSNESS_TERNARY_SCENARIO: &str =
    include_str!("../content/scenarios/consciousness-ternary-conformance.bscn");
const CONSCIOUSNESS_TERNARY_RULES: &str = include_str!("../content/rules/consciousness.bsl");

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

/// The Production port's own composition golden (P27, issue #565, Task 5;
/// RE-PINNED, fix round, adversarial verification): all FIVE
/// `production/*` rules against the nine-social-class/five-territory
/// conformance world in one tick — the port train's entry into the Rust
/// byte gate. `production_conformance.rs`'s own suite already pins every
/// STRUCTURAL claim this hash summarizes (the wealth ledger, the employer
/// accumulation, the idle-worker hash-neutral vector, the extraction-
/// intensity broadcast — now matching the frozen mirror's single-territory
/// attribution exactly, the fix round's own discharge of D136); this golden
/// exists to catch ANY unintentional drift a structural assertion happens
/// not to cover — the same class of blind spot
/// `territory_conformance_hashes_are_pinned`'s own header names. The
/// re-pin (both hashes AND the fired count moved: the pack gained a fifth
/// rule, `production/p0-production-total-reset`, and the fixture gained a
/// fifth territory/ninth social class, `t-tight`/`worker-tight`, MINOR-2)
/// is a measurement, not a ceremony (III.13 baseline ceremonies apply to
/// `tests/baselines/**`, not this crate's own goldens) — this golden is new
/// enough in this repo's history that its own prior value was never load-
/// bearing outside this crate. The five OTHER pre-existing pins above are
/// untouched by this content pair's own load/rules.
#[test]
fn production_conformance_hashes_are_pinned() {
    let report = run_once(PRODUCTION_SCENARIO, PRODUCTION_RULE).expect("production tick");
    assert_eq!(
        hex(&report.before),
        "83192431e51d9be36aea347cec0861ebe352e47ee8f9bce4f39840f3e581ad4b",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         production-conformance.bscn (nine social classes + five \
         territories + twelve edges)"
    );
    assert_eq!(
        hex(&report.after),
        "1538162e443afd4b1dcc020bec886e616c91bc680dffce50e52d48df4af8f1eb",
        "post-tick hash moved — all five rules' combined tick-1 output"
    );
    assert_eq!(
        report.fired, 17,
        "5 (p0) + 3 (p1) + 3 (p2) + 1 (p3) + 5 (p4) = 17 — the fix round's own predicted \
         arithmetic, verified rather than trusted"
    );
}

/// The WorldView mint's own golden (ADR204 W10, ceremony ADR206): the
/// substrate LOAD of the mint scenario, byte-pinned. What this pin
/// guards is the world's graph facts — the canonical state hash covers
/// nodes/attributes/edges/hyperedges/edge attributes ONLY, so the
/// `defenum` declaration itself does not move these bytes; the ruled
/// member ORDER (REVOLUTIONARY=0 / LIBERAL=1 / FASCIST=2 — declaration
/// order IS the storage ordinal, ADR195) is guarded by the explicit
/// registry assertion in `worldview_member_order_is_the_ruled_ordinal`
/// below, not by this hash. The pack's one rule is a never-firing load
/// probe (the rule pipeline refuses a zero-rule content set; the idiom
/// is production_conformance.rs's own): the guard is false for every
/// legal population, so `fired == 0` and `before == after` are the mint
/// stage's honest expectations (the measured-ternary consumers land
/// with the port train), NOT a bug — exactly the emit-only logic the
/// organization golden's own header spells out, one step further.
#[test]
fn worldview_foundation_hashes_are_pinned() {
    let report = run_once(WORLDVIEW_SCENARIO, WORLDVIEW_RULES).expect("worldview-foundation tick");
    assert_eq!(
        hex(&report.before),
        "098ef6bd62ebc072de94d370242430d84b1b8cf2223b3b190b359ed6e871edbf",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         worldview-foundation.bscn (the mint world's graph-fact pin)"
    );
    assert_eq!(
        hex(&report.after),
        "098ef6bd62ebc072de94d370242430d84b1b8cf2223b3b190b359ed6e871edbf",
        "post-tick hash moved — the probe rule never fires, so this \
         equals `before` by construction; a divergence here means the \
         tick mutated state without a firing rule, which is its own bug"
    );
    assert_eq!(
        report.fired, 0,
        "the worldview mint pack's load probe never fires (its guard is \
         false for every legal population)"
    );
}

/// The ruled ordinal order, guarded EXPLICITLY (task-review finding,
/// plan amended 2026-08-15): the canonical state hash covers graph
/// facts only, so the `defenum` declaration never moves the byte pin
/// above — THIS registry assertion, not the hash, is what guards
/// REVOLUTIONARY=0 / LIBERAL=1 / FASCIST=2. Declaration order IS the
/// storage ordinal (ADR195); a reordered, renamed, or dropped member
/// fails here loudly.
#[test]
fn worldview_member_order_is_the_ruled_ordinal() {
    let mut graph = HypergraphStore::new();
    let loaded =
        load_scenario(WORLDVIEW_SCENARIO, &mut graph).expect("worldview-foundation loads clean");
    let ty = loaded
        .enums
        .resolve("WorldView")
        .expect("the WorldView defenum is declared");
    assert_eq!(loaded.enums.ordinal(ty, "REVOLUTIONARY"), Some(0));
    assert_eq!(loaded.enums.ordinal(ty, "LIBERAL"), Some(1));
    assert_eq!(loaded.enums.ordinal(ty, "FASCIST"), Some(2));
}

/// The consciousness class-surface ternary port's own composition golden
/// (ADR204 W10, issue #588, Task 1): the FIRST committed `probability`-lane
/// deffields plus the pack's first rule (`consciousness/p0-position`),
/// against the five-class-plus-org conformance world in one tick — the
/// port train's entry into the Rust byte gate. `consciousness_ternary_
/// conformance.rs`'s posture test already pins every STRUCTURAL claim this
/// hash summarizes (the UNPOSITIONED witness's loud absence, the exact
/// (0, 1, 0) positioning, the one-home dominant-worldview absence, the
/// untouched positioned seeds); this golden exists to catch ANY
/// unintentional drift a structural assertion happens not to cover — the
/// same class of blind spot `territory_conformance_hashes_are_pinned`'s
/// own header names. RE-PINNED in the same task's fix round (controller
/// rulings 1-3: the dominant write came out, the WAGES edge machinery was
/// replaced by the class-side wages-received field, the micros seeds went
/// raw) — this golden was minted in this task, so the re-pin is a
/// measurement, not a ceremony (III.13 baseline ceremonies apply to
/// `tests/baselines/**`, not this crate's own goldens).
#[test]
fn consciousness_ternary_foundation_hashes_are_pinned() {
    let report = run_once(CONSCIOUSNESS_TERNARY_SCENARIO, CONSCIOUSNESS_TERNARY_RULES)
        .expect("consciousness-ternary tick");
    assert_eq!(
        hex(&report.before),
        "c6480564519c29f5d8e5d22ad5e1c4186f743a6d80b9f09bc58203a3a9164730",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         consciousness-ternary-conformance.bscn (five social classes + one \
         organization + three SOLIDARITY edges)"
    );
    assert_eq!(
        hex(&report.after),
        "bd9226d26158a550646f9221efc7115ef7f3ce307d0b649c563f43052edf39b0",
        "post-tick hash moved — the p0-position rule's tick-1 output"
    );
    assert_eq!(
        report.fired, 1,
        "p0-position fires exactly once (class-emergent)"
    );
}

/// The ruled ordinal order, guarded EXPLICITLY for the port's own re-
/// declaration (spike 2's verdict: one `(scenario ...)` form per load —
/// `scenario.rs:313-318` — so the ternary conformance scenario re-declares
/// `WorldView` rather than sharing worldview-foundation.bscn's registry).
/// The same law the mint's own `worldview_member_order_is_the_ruled_
/// ordinal` pins above: declaration order IS the storage ordinal (ADR195);
/// a reordered, renamed, or dropped member fails here loudly.
#[test]
fn consciousness_ternary_worldview_member_order_is_the_ruled_ordinal() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(CONSCIOUSNESS_TERNARY_SCENARIO, &mut graph)
        .expect("consciousness-ternary-conformance loads clean");
    let ty = loaded
        .enums
        .resolve("WorldView")
        .expect("the WorldView defenum is re-declared in the port scenario");
    assert_eq!(loaded.enums.ordinal(ty, "REVOLUTIONARY"), Some(0));
    assert_eq!(loaded.enums.ordinal(ty, "LIBERAL"), Some(1));
    assert_eq!(loaded.enums.ordinal(ty, "FASCIST"), Some(2));
}
