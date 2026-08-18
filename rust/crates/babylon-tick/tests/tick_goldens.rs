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

use babylon_bsl::scenario::{load_scenario, load_scenario_with_prelude};
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_tick::{hex, run_once, run_once_with_prelude};

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
const SOLIDARITY_SCENARIO: &str = include_str!("../content/scenarios/solidarity-conformance.bscn");
const SOLIDARITY_RULE: &str = include_str!("../content/rules/solidarity.bsl");
// Train B item 4 (#591, D157): the declaration prelude the consciousness-
// ternary golden now shares its WorldView type through, rather than
// re-declaring it — see the .bscn's own header for the retirement note.
const WORLDVIEW_PRELUDE: &str = include_str!("../content/declarations/worldview.bscn");

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
/// (ADR204 W10, issue #588, Tasks 1-2): the FIRST committed `probability`-lane
/// deffields, the pack's first rule (`consciousness/p0-position`), and the
/// measured readout (`consciousness/p8-dominant-worldview`), against the
/// thirteen-class-plus-org conformance world in one tick — the
/// port train's entry into the Rust byte gate. The
/// `consciousness_ternary_conformance.rs` posture test already pins every
/// STRUCTURAL claim this hash summarizes (the UNPOSITIONED witness's loud
/// absence, the exact (0, 1, 0) positioning, the untouched positioned
/// seeds); this golden exists to catch ANY unintentional drift a structural
/// assertion happens not to cover — the same class of blind spot
/// `territory_conformance_hashes_are_pinned`'s own header names. RE-PINNED
/// four times in this train (Task-1 fix round 1, controller rulings 1-3:
/// the dominant write came out, the WAGES edge machinery was replaced by
/// the class-side wages-received field, the micros seeds went raw; Task-1
/// fix round 2: agitation re-typed to the verbatim-f64 int lane with zero
/// seeds; Task 2: the p8-dominant-worldview read path landed and the world
/// gained the eight tv-* read-path fixtures, moving both hashes and the
/// fired count 1 -> 12; Task 3: the measured update law p1..p7 landed —
/// the routed ternaries, the produced agitation, the inboxes (p1's reset
/// writes 0 onto the eight tv-* fixtures' absent solidarity-inbox: the
/// controller-flagged hash-visible machinery write), the wage balances, the
/// persisted baselines — moving the post-tick hash and the fired count
/// 12 -> 50; the pre-tick hash is unchanged) — this golden was minted in
/// this train, so the re-pins are measurements, not ceremonies (III.13
/// baseline ceremonies apply to `tests/baselines/**`, not this crate's own
/// goldens). Every structural claim the post-tick hash summarizes is pinned
/// exactly in `consciousness_ternary_conformance.rs` against the
/// dual-implementation oracle.
///
/// FIFTH RE-PIN — Train B item 3 (issue #591, D151's discharge): WAGES
/// edges + `wages/value-flow` seeding restored the frozen fold-sum via
/// push-over-pull; `wages-received` retired; BOTH hashes re-pinned
/// (attribute-set change, zero value drift — proven by
/// `consciousness_ternary_conformance.rs` passing with only the two field
/// re-points); fired 50 -> 63. The attribute-set delta is exactly the
/// brief's own predicted shape, verified rather than assumed: pre-tick
/// state differs ONLY by −3 `wages-received` node attributes, +3 WAGES
/// edges, +3 `wages/value-flow` edge attributes (+0 `wages-inbox` —
/// unseeded); post-tick state differs ONLY by −`wages-received`,
/// +`wages-inbox` on the reset/pushed classes. The fired-count spike (Step
/// 3, measured against the EXPECTED "employer only, +1" hypothesis): the
/// mirrored `active`-gated shape does not discriminate on WAGES-edge
/// presence, so all thirteen SOCIAL_CLASS subjects fire (not one) — the
/// measured arithmetic is 50 + 13 = 63 (tick 1), 49 + 13 = 62 (tick 2, p0
/// not re-firing) — recorded honestly per the house pattern this file's own
/// `production_conformance_hashes_are_pinned` header sets.
///
/// LOAD-MECHANISM CHANGE ONLY, HASHES UNCHANGED — Train B item 4 (issue
/// #591, D157): the `.bscn`'s own `(defenum WorldView …)` re-declaration
/// came out; the WorldView type now arrives from the shared declaration
/// prelude (`content/declarations/worldview.bscn`) via
/// `run_once_with_prelude`, and the scenario's `deffield … enum WorldView`
/// resolves against the SAME registry contents it always did
/// (`EnumRegistry::declare`'s identical-recognition arm is not even reached
/// here — the `.bscn` no longer re-declares at all). `defenum` declarations
/// are unhashed and the graph content is byte-identical, so BOTH hashes and
/// `fired` (63) below are UNCHANGED from the fifth re-pin — verified, not
/// assumed (this is exactly the byte-neutrality proof the brief demanded;
/// see `consciousness_ternary_conformance.rs` for the companion
/// value-level proof).
#[test]
fn consciousness_ternary_foundation_hashes_are_pinned() {
    let report = run_once_with_prelude(
        CONSCIOUSNESS_TERNARY_SCENARIO,
        WORLDVIEW_PRELUDE,
        CONSCIOUSNESS_TERNARY_RULES,
    )
    .expect("consciousness-ternary tick");
    assert_eq!(
        hex(&report.before),
        "e2582dd4f3537a6baa26fdb273e9aaf39299ab4994cf0dcf2664a90b920821fe",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         consciousness-ternary-conformance.bscn (thirteen social classes + one \
         organization + three SOLIDARITY edges + three WAGES edges — the \
         Train B item 3 re-pin, D151's discharge)"
    );
    assert_eq!(
        hex(&report.after),
        "52ffb5e332cca9bddcaf9b77fcdf3ed1efe8e30e9abf3176fe0569e7aa47ff91",
        "post-tick hash moved — the ten-rule pack's combined tick-1 output \
         (p0's positioning, p1..p7's measured update law plus the new \
         p2-wages-push, p8's readout) — attribute-set change only, zero \
         value drift (Train B item 3's re-pin). RE-PINNED (#491 T1, D183, \
         controller adjudication 2026-08-18: C1/p5-agitation's proportional \
         rent term, licensed by D181, plus D182/D183's product/division \
         licensing that unblocked p6-route's load path): class-bribed's \
         agitation/l/f VALUES moved (not the attribute set) — see \
         consciousness_ternary_conformance.rs's re-measured assertions and \
         its module-header post-repair note for the exact numbers and the \
         ternary-routing consequence (the tick-2 FASCIST flip no longer \
         happens). report.before, above, is UNCHANGED — no new graph \
         content, only rule text moved."
    );
    assert_eq!(
        report.fired, 63,
        "p0:1 + p1:11 (inbox reset on every positioned class) + p2:1 + \
         p2-wages-push:13 (every active SOCIAL_CLASS subject — the mirrored \
         active gate does not discriminate on WAGES-edge presence, so the \
         for-each idiom fires on edgeless subjects too; only employer's \
         three WAGES edges write) + p3:6 (r > 0.3 sources) + p4:3 + p5:3 + \
         p6:11 + p7:3 + p8:11 — the per-rule breakdown is pinned in \
         consciousness_ternary_conformance.rs"
    );
}

/// The prelude's own ordinal, guarded EXPLICITLY — final whole-branch
/// review item 2 (#591): the declared test death below rests on a claim
/// ("byte-identical to the mint's declaration") that only a comment
/// enforced. `worldview_member_order_is_the_ruled_ordinal` above loads
/// ONLY `WORLDVIEW_SCENARIO` (the mint) — it never loads
/// `WORLDVIEW_PRELUDE`, which is what `consciousness_ternary_foundation_
/// hashes_are_pinned` above ACTUALLY consumes via `run_once_with_prelude`.
/// This is the same failure mode Task 3's F1 caught one PR earlier (a
/// byte-identity claim guarded only by a comment), recurring unnoticed
/// inside the same train. This test closes it by asserting the three
/// ordinals as declared by `WORLDVIEW_PRELUDE` itself, loaded through the
/// real loader (`load_scenario_with_prelude`) against a minimal probe
/// scenario — not by prose about what the mint's line happens to match.
#[test]
fn worldview_prelude_member_order_is_the_ruled_ordinal() {
    let mut graph = HypergraphStore::new();
    let loaded =
        load_scenario_with_prelude(WORLDVIEW_PRELUDE, "(scenario t/ordinal-probe)", &mut graph)
            .expect("the worldview prelude loads clean against an empty probe scenario");
    let ty = loaded
        .enums
        .resolve("WorldView")
        .expect("the WorldView defenum is declared by the prelude");
    assert_eq!(loaded.enums.ordinal(ty, "REVOLUTIONARY"), Some(0));
    assert_eq!(loaded.enums.ordinal(ty, "LIBERAL"), Some(1));
    assert_eq!(loaded.enums.ordinal(ty, "FASCIST"), Some(2));
}

// The `consciousness_ternary_worldview_member_order_is_the_ruled_ordinal`
// test that lived here (the ternary port's own re-declaration guard) is a
// DECLARED TEST DEATH — Train B item 4 (#591, D157): the prelude
// composition (above) makes the re-declaration it guarded IMPOSSIBLE (the
// `.bscn` no longer declares `WorldView` at all), so the assertion it made
// has no subject left to guard. `worldview_prelude_member_order_is_the_
// ruled_ordinal` (immediately above) is the ordinal home for what this
// golden's tick actually reads — the prelude — asserted executably rather
// than by a comment's claim that the mint's line happens to match it.

/// The Solidarity port train's own composition golden (issue #557 umbrella,
/// Task 4): the ONE `solidarity/p0-transmit` rule against the
/// twenty-two-social-class conformance world in one tick — the port
/// train's entry into the Rust byte gate. `solidarity_conformance.rs`'s own
/// suite already pins every STRUCTURAL claim this hash summarizes (every
/// witness target's post-tick value, the three skip gates, the
/// multi-inbound last-write-wins divergence from frozen D-record 2, the
/// clamp, the exact-0.6 boundary, the nine ordered CONSCIOUSNESS_TRANSMISSION
/// / MASS_AWAKENING events) against the dual-implementation oracle
/// (`content/scenarios/solidarity_conformance.py`, Task 4); this golden
/// exists to catch ANY unintentional drift a structural assertion happens
/// not to cover — the same class of blind spot
/// `territory_conformance_hashes_are_pinned`'s own header names. Measured,
/// never derived (`tick_goldens.rs`'s own doctrine, lines 21-23 above): run
/// once, `hex(&report.before)`/`hex(&report.after)` read back and pasted
/// here verbatim. New in this train, so this is a measurement, not a
/// ceremony (III.13 baseline ceremonies apply to `tests/baselines/**`, not
/// this crate's own goldens); it touches none of the 8 existing pins above.
#[test]
fn solidarity_conformance_hashes_are_pinned() {
    let report = run_once(SOLIDARITY_SCENARIO, SOLIDARITY_RULE).expect("solidarity tick");
    assert_eq!(
        hex(&report.before),
        "20124f5ca91da3cb30fba41bc373175fdf3b06dc82f3c3b162da172951bb29de",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         solidarity-conformance.bscn (twenty-two social classes + twelve \
         SOLIDARITY edges)"
    );
    assert_eq!(
        hex(&report.after),
        "62212dab6bdc255f334eca1ff2260e2ad939776f15aee744ae771ab1be30b3d1",
        "post-tick hash moved — the one-rule pack's tick-1 output (fourteen \
         subjects fire, nine transmit-or-awaken events, one multi-inbound \
         last-write-wins divergence from frozen). RE-PINNED (#491 T1 S1, \
         Director sitting 2026-08-18: repair-now+ceremony): p0-transmit's \
         write is now a kind-coherent convex combination, algebraically \
         identical to `target + delta` but not bit-identical for the \
         multi-inbound witness's non-power-of-2 strength (0.3) — a 1-ULP \
         rounding-order drift on exactly two attribute bytes \
         (multi-target's stored value and one CONSCIOUSNESS_TRANSMISSION \
         payload field), predicted in \
         reports/kind-straddle-repair-options-2026-08-18.md §2.1 and \
         confirmed by solidarity_conformance.rs's own updated assertions. \
         report.before is UNCHANGED (no new graph content, only the rule \
         text moved)."
    );
    assert_eq!(
        report.fired, 14,
        "14 of 22 witness nodes have active=1 and revolutionary > \
         solidarity/activation-threshold (0.3) — solidarity_conformance.rs's own \
         the_conformance_world_loads_with_the_declared_census pins the same count"
    );
}

const DECOMPOSITION_SCENARIO: &str =
    include_str!("../content/scenarios/decomposition-conformance.bscn");
const DECOMPOSITION_DELAY_SCENARIO: &str =
    include_str!("../content/scenarios/decomposition-delay-conformance.bscn");
const DECOMPOSITION_RULE: &str = include_str!("../content/rules/decomposition.bsl");

/// The Decomposition port's own composition golden (Checkpoint A campaign,
/// #591 family, Task 4 — closes Pack A): all SIX `decomposition/*` rules
/// against the fallback-trigger conformance world (`la-dying`'s wealth 400
/// already below subsistence 500 at tick 1, so `CLASS_DECOMPOSITION` fires
/// the SAME tick as the SUPERWAGE_CRISIS early warning —
/// `decomposition_conformance.rs`'s own module doc explains why the frozen
/// mirror shows both firing together). `decomposition_conformance.rs`'s own
/// suite already pins every STRUCTURAL claim this hash summarizes (the
/// additive enforcer intake, the overwrite IP intake, the non-conserving LA
/// deactivation, the flattened CLASS_DECOMPOSITION payload); this golden
/// exists to catch ANY unintentional drift a structural assertion happens
/// not to cover — the same class of blind spot
/// `territory_conformance_hashes_are_pinned`'s own header names.
#[test]
fn decomposition_conformance_hashes_are_pinned() {
    let report = run_once(DECOMPOSITION_SCENARIO, DECOMPOSITION_RULE).expect("decomposition tick");
    assert_eq!(
        hex(&report.before),
        "4001e15449fbf467624417f3c4a9cca22e27bdea3320c81669808c5940a7eb8a",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         decomposition-conformance.bscn (five social classes + one carrier)"
    );
    assert_eq!(
        hex(&report.after),
        "6bcc49d18b1e2494adf96bada45425616b955373293494d314ecdf20679d9b0f",
        "post-tick hash moved — all six rules' combined tick-1 output: p01's \
         census, p02's SUPERWAGE_CRISIS latch, p03's fallback-triggered fire, \
         p04/p05's intake, p06's LA deactivation"
    );
    assert_eq!(
        report.fired, 10,
        "p01:5 (every SOCIAL_CLASS subject, D127 unconditional) + p02:1 \
         (la-dying only) + p03:1 (the one carrier) + p04:1 (enforcer-seed) \
         + p05:1 (ip-seed) + p06:1 (la-dying)"
    );
}

/// The Decomposition port's delay-path companion golden (Task 4 Step 4):
/// ONE tick against `decomposition-delay-conformance.bscn` — the early
/// warning fires, but `CLASS_DECOMPOSITION` does not (the 52-tick delay has
/// not elapsed at tick 1), so p04-p06 never match their `fire-tick == tick`
/// gate this tick. `decomposition_conformance.rs`'s own
/// `the_delay_path_emits_the_warning_at_tick_1_and_decomposes_at_tick_53`/
/// `the_delay_path_does_not_decompose_at_tick_52` pin the full multi-tick
/// lifecycle structurally; this golden pins tick 1 alone against silent
/// drift, the same role every other pair in this file plays.
#[test]
fn decomposition_delay_conformance_hashes_are_pinned() {
    let report = run_once(DECOMPOSITION_DELAY_SCENARIO, DECOMPOSITION_RULE)
        .expect("decomposition-delay tick");
    assert_eq!(
        hex(&report.before),
        "40f0facb177fb535af415f99f70244663cc0ffe4fc26352efc91d308301f5e1e",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         decomposition-delay-conformance.bscn (six social classes + one \
         carrier)"
    );
    assert_eq!(
        hex(&report.after),
        "0eaf7f1459559645510efd57c71739f3ef8813409f3944b9eba51492d141748b",
        "post-tick hash moved — the pack's tick-1 output: only p01's census \
         and p02's SUPERWAGE_CRISIS latch write anything (p03 folds but does \
         not fire; p04-p06 never match fire-tick == tick this tick)"
    );
    assert_eq!(
        report.fired, 8,
        "p01:6 (every SOCIAL_CLASS subject, D127 unconditional) + p02:1 \
         (la-approaching only) + p03:1 (the one carrier) + p04:0 + p05:0 + \
         p06:0 (should-fire is false — the delay has not elapsed)"
    );
}

// ---------------------------------------------------------------------
// Task 8 — the remaining golden pins: the four Pack B scenarios plus the
// joint five-phase arc (Checkpoint A campaign, #591 family). The 11
// pre-existing pins above (verified by direct count, `tick_goldens.rs`'s
// own `fn .*hashes_are_pinned` tally — 9 pre-Pack-A + Pack A's 2) stay
// byte-identical; none of Task 8's own edits touch any content pair above
// this comment.
// ---------------------------------------------------------------------

const CONTROL_RATIO_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-conformance.bscn");
const CONTROL_RATIO_REVOLUTION_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-revolution-conformance.bscn");
const CONTROL_RATIO_WITHIN_CAPACITY_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-within-capacity-conformance.bscn");
const CONTROL_RATIO_ZERO_ENFORCER_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-zero-enforcer-conformance.bscn");
const CONTROL_RATIO_RULE: &str = include_str!("../content/rules/control-ratio.bsl");

/// The ControlRatio Pack B primary golden (Task 8, closes the remaining
/// Pack B pins): all FOUR `control-ratio/*` rules against the PRIMARY
/// (genocide) conformance world in one tick — this pack's own entry into
/// the Rust byte gate, alongside `decomposition_conformance_hashes_are_
/// pinned`'s own role for Pack A. `control_ratio_conformance.rs`'s own
/// suite already pins every STRUCTURAL claim this hash summarizes (the
/// two-role prisoner census, the `<=` boundary, the guard-split emit, the
/// terminal-decision routing); this golden exists to catch ANY
/// unintentional drift a structural assertion happens not to cover — the
/// same class of blind spot `territory_conformance_hashes_are_pinned`'s
/// own header names.
#[test]
fn control_ratio_conformance_hashes_are_pinned() {
    let report = run_once(CONTROL_RATIO_SCENARIO, CONTROL_RATIO_RULE).expect("control-ratio tick");
    assert_eq!(
        hex(&report.before),
        "54f7a559a3c047561979994bd058460a3bd12ba361511117bb5227a32f4ad583",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         control-ratio-conformance.bscn (six social classes + one carrier)"
    );
    assert_eq!(
        hex(&report.after),
        "cececdab38bc6ba483baf60ee4df32cb4043073ce18fdd54ce9c866c922b6e5b",
        "post-tick hash moved — all four rules' combined tick-1 output: c01's \
         census, c02's carrier publication, c03's CONTROL_RATIO_CRISIS, c04's \
         GENOCIDE TERMINAL_DECISION"
    );
    assert_eq!(
        report.fired, 9,
        "c01:6 (every SOCIAL_CLASS subject, D127 unconditional) + c02:1 \
         (the one carrier) + c03:1 (the crisis) + c04:1 (the terminal decision)"
    );
}

/// The ControlRatio Pack B revolution companion golden — identical
/// structure to the primary world, organization 0.2 -> 0.6, routing
/// REVOLUTION instead of GENOCIDE.
#[test]
fn control_ratio_revolution_conformance_hashes_are_pinned() {
    let report = run_once(CONTROL_RATIO_REVOLUTION_SCENARIO, CONTROL_RATIO_RULE)
        .expect("control-ratio-revolution tick");
    assert_eq!(
        hex(&report.before),
        "af67a81e16e480adfc621e8617eb1edef99921a45e67b5544451d8f10edc4c1f",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         control-ratio-revolution-conformance.bscn (six social classes + one carrier)"
    );
    assert_eq!(
        hex(&report.after),
        "0ebd2a90c4868a84dd8547c5c37a99fd44cd612f2cbc53c06163847e7c34cb0a",
        "post-tick hash moved — all four rules' combined tick-1 output, \
         routing REVOLUTION (organization 0.6 >= revolution-threshold 0.5)"
    );
    assert_eq!(
        report.fired, 9,
        "c01:6 + c02:1 + c03:1 (the crisis) + c04:1 (the terminal decision)"
    );
}

/// The ControlRatio Pack B within-capacity companion golden — the `<=`
/// boundary (prisoner population 40 == enforcer population 10 *
/// control-capacity 4 exactly): NO crisis, so c03/c04 never fire this tick.
#[test]
fn control_ratio_within_capacity_conformance_hashes_are_pinned() {
    let report = run_once(CONTROL_RATIO_WITHIN_CAPACITY_SCENARIO, CONTROL_RATIO_RULE)
        .expect("control-ratio-within-capacity tick");
    assert_eq!(
        hex(&report.before),
        "f4c8d6b0a12047e713ec3d995cb70f519a4136dadb852192116d237ecdb0834a",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         control-ratio-within-capacity-conformance.bscn (three social classes + one carrier)"
    );
    assert_eq!(
        hex(&report.after),
        "67aa4f7bfcc2ad807331354ea786001a6dc46a7ea5a7514c87ad963f90860470",
        "post-tick hash moved — c01/c02's own tick-1 output; c03's `when` \
         (prisoner-population > max-controllable) is false at the exact `<=` \
         boundary, so c03/c04 never fire"
    );
    assert_eq!(
        report.fired, 4,
        "c01:3 (every SOCIAL_CLASS subject) + c02:1 (the one carrier) + \
         c03:0 + c04:0 (within capacity — no crisis, no terminal decision)"
    );
}

/// The ControlRatio Pack B zero-enforcer companion golden — BLOCKER-4's
/// guard-split branch: a REAL, active, zero-population CARCERAL_ENFORCER
/// class (not an absent one), so `max-controllable` is 0 and ANY nonzero
/// prisoner population clears the `<=` boundary; the crisis payload omits
/// `actual-ratio`/`control-ratio` entirely (loud absence, not `float("inf")`).
#[test]
fn control_ratio_zero_enforcer_conformance_hashes_are_pinned() {
    let report = run_once(CONTROL_RATIO_ZERO_ENFORCER_SCENARIO, CONTROL_RATIO_RULE)
        .expect("control-ratio-zero-enforcer tick");
    assert_eq!(
        hex(&report.before),
        "62f02edb2de87305b34ec7efd5b0a638929300a60ac8473aace3e9b86ccad100",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         control-ratio-zero-enforcer-conformance.bscn (three social classes + one carrier)"
    );
    assert_eq!(
        hex(&report.after),
        "897c1939b9f798026ddc41d9732b0b676a0b628f00b8a845a1c8261d5f725204",
        "post-tick hash moved — all four rules' combined tick-1 output, the \
         zero-enforcer guard-split branch (BLOCKER-4), routing GENOCIDE \
         (organization 0.4 < revolution-threshold 0.5)"
    );
    assert_eq!(
        report.fired, 6,
        "c01:3 (every SOCIAL_CLASS subject) + c02:1 + c03:1 (the crisis, \
         zero-enforcer branch) + c04:1 (the terminal decision) — three \
         SOCIAL_CLASS nodes here, not six (unlike the primary/revolution \
         worlds), so c01's own count is half theirs"
    );
}

const VITALITY_ATTRITION_SCENARIO: &str =
    include_str!("../content/scenarios/vitality-attrition-conformance.bscn");
const VITALITY_ATTRITION_RULE: &str = include_str!("../content/rules/vitality-attrition.bsl");

/// The K=16 wealth-mass carrier's own golden (#491 T4, Phase 1 — "the
/// carrier, inert"; ADR194 R1). `vitality_attrition_conformance.rs`'s own
/// posture suite already pins every STRUCTURAL claim this hash summarizes
/// (the exact-1.0 mass sums, the absence fence, cut monotonicity/
/// positivity, η/τ's ruled values, the Currency-lane round-trip); this
/// golden exists to catch ANY unintentional drift a structural assertion
/// happens not to cover — the same class of blind spot
/// `territory_conformance_hashes_are_pinned`'s own header names.
///
/// `before == after` here is not a bug, and neither is the sixteenth
/// pre-existing pin above staying untouched by this one: the carrier's own
/// probe rule (`content/rules/vitality-attrition.bsl`) never fires (its
/// guard is false for every legal population — the SAME never-firing-probe
/// idiom `worldview_foundation_hashes_are_pinned`'s own header explains),
/// so this tick moves no state — exactly the load-only smoke the carrier
/// is at this phase (no rule reads the sixteen masses, the fifteen cuts,
/// η or τ yet; T5/T6 are the tasks that give this namespace its first real
/// consumer). What this pin actually guards is the substrate LOAD:
/// six social classes, the Currency-lane re-seed of `wealth`/`s-bio`/
/// `s-class` (T3, OQ-J — this is the FIRST conformance world in this crate
/// to declare a `currency` node attribute, so `CanonicalState` section
/// `0x06` (D189/D190) materializes for it; this pin is that section's
/// first real-content byte measurement, not derived from any pre-existing
/// pin above), the sixteen-mass carrier (five explicit 16-value vectors
/// plus one class carrying none at all), the fifteen grid-cut defconsts,
/// and η/τ. Measured, never derived: `run_once` against the committed
/// content, `hex(&report.before)`/`hex(&report.after)` read back and
/// pasted here verbatim (`tick_goldens.rs`'s own doctrine, lines 21-23
/// above). New in this train, so this is a measurement, not a ceremony
/// (III.13 baseline ceremonies apply to `tests/baselines/**`, not this
/// crate's own goldens); the SIXTEEN pre-existing pins above (verified by
/// direct count against this checkout's BASE, `ec3e1867` — sixteen
/// `fn .*hashes_are_pinned` tests, eighteen `#[test]` functions total
/// counting the two ordinal guards) stay byte-identical, proven by running
/// this crate's full suite both before and after this pin's own addition.
#[test]
fn vitality_attrition_carrier_hashes_are_pinned() {
    let report = run_once(VITALITY_ATTRITION_SCENARIO, VITALITY_ATTRITION_RULE)
        .expect("vitality-attrition carrier tick");
    assert_eq!(
        hex(&report.before),
        "d93402d63a499c47b4361e036ce6a9f7d846766fda0192bde9add403434aa7e0",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         vitality-attrition-conformance.bscn (six social classes, the \
         Currency-lane re-seed, the K=16 mass carrier, the fifteen cuts, \
         η and τ) — the FIRST pin in this crate to exercise CanonicalState \
         section 0x06 with real content"
    );
    assert_eq!(
        hex(&report.after),
        "d93402d63a499c47b4361e036ce6a9f7d846766fda0192bde9add403434aa7e0",
        "post-tick hash moved — the carrier's own probe rule never fires \
         (guard false for every legal population), so this equals `before` \
         by construction; a divergence here means the tick mutated state \
         without a firing rule, which is its own bug, exactly as \
         `organization_foundation_hashes_are_pinned`'s own header explains"
    );
    assert_eq!(
        report.fired, 0,
        "the load-only carrier probe never fires — no rule reads the \
         sixteen masses, the fifteen cuts, η or τ at this phase"
    );
}

const CARCERAL_ARC_SCENARIO: &str =
    include_str!("../content/scenarios/carceral-arc-conformance.bscn");

/// The joint carceral arc's own composition golden (Task 8, the train's
/// acceptance test) — TICK 1 ALONE, the same single-tick convention every
/// other pair in this file follows: `carceral_arc_conformance.rs`'s own
/// multi-tick `TickSession` suite already pins the FULL five-phase
/// sequence (ticks 1/53/105/106) structurally; this golden exists to catch
/// ANY unintentional tick-1 drift a structural assertion happens not to
/// cover — the same class of blind spot `territory_conformance_hashes_are_
/// pinned`'s own header names, applied to the concatenation of BOTH packs
/// for the first time in this crate's own golden surface.
#[test]
fn carceral_arc_conformance_hashes_are_pinned() {
    let rule_src = format!("{DECOMPOSITION_RULE}\n{CONTROL_RATIO_RULE}");
    let report = run_once(CARCERAL_ARC_SCENARIO, &rule_src).expect("carceral-arc tick");
    assert_eq!(
        hex(&report.before),
        "504a4515c4e6d4d4c369a535c58a21ab98e8ee37ba852819c7b4893473881e74",
        "pre-tick hash moved — this is the SUBSTRATE'S load of \
         carceral-arc-conformance.bscn (five social classes + one carrier)"
    );
    assert_eq!(
        hex(&report.after),
        "04b2a84623e25fdf7fd7761e3c591baa8b42aa96300c76b02caca59e0c74b3d6",
        "post-tick hash moved — BOTH packs' combined tick-1 output: c01-c04's \
         readiness gate stays closed (decomposition-fired-known unwritten \
         until p03 runs, later in byte order), p01's census, p02's \
         SUPERWAGE_CRISIS latch, p03's carrier fold (should-fire false at \
         tick 1 — the delay path)"
    );
    assert_eq!(
        report.fired, 13,
        "c01:5 (every SOCIAL_CLASS subject) + c02:1 (the carrier) + c03:0 \
         (readiness gate closed) + c04:0 + p01:5 (every SOCIAL_CLASS \
         subject) + p02:1 (la-approaching's early warning) + p03:1 (the \
         carrier fold, always fires, should-fire false) + p04:0 + p05:0 + \
         p06:0 (fire-tick never reaches tick 1 on the delay path)"
    );
}
