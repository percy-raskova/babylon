//! Posture suite for the K=16 wealth-mass carrier (#491 T4, Phase 1 —
//! "the carrier, inert"; design doc §6.2 H1; ADR194 R1).
//!
//! # What this file is, and is not
//!
//! `content/scenarios/vitality-attrition-conformance.bscn` declares and
//! seeds the carrier — sixteen per-class wealth-mass shares, the fifteen
//! grid cuts, the household→person crossing (`η`), and the subsistence
//! horizon (`τ`) — but **no rule reads any of it**. The scenario's own
//! probe rule (`content/rules/vitality-attrition.bsl`) is a load-only
//! smoke, never firing. This suite therefore asserts LOAD-TIME facts
//! only, read directly off the substrate through
//! [`babylon_graph::substrate::GraphSubstrate`] — never through a BSL
//! rule's own binding/effect machinery, which does not exist for these
//! fields yet. That absence is the point: Phase 1 supplies the carrier,
//! not the derivation (design doc §12 item 1 — this train does not
//! discharge OQ-D's C/G/P derivation under Axiom A0).
//!
//! # Unit-system authority
//!
//! Every construct this file names — `wealth-mass-k`, `cut-k`, `η`, `τ` —
//! is DEFINED in `reports/subsistence-unit-reconciliation-2026-08-17.md`
//! (§3 the unit table, §3.1 the crossing, §4 τ, §9 the Aleksandrov trace).
//! This file cites that record; it does not re-derive it.
//!
//! # The five posture legs (§9/T4.1, verbatim)
//!
//! 1. A seeded class reads all 16 masses and they sum to exactly `1.0` in
//!    the stored `f64` (largest-remainder apportionment is I1's law —
//!    this hand-authored fixture's own values are chosen to sum exactly
//!    without needing any apportionment at all: every class's nonzero
//!    entries are binary64-exact dyadic fractions, so no residue exists
//!    to apportion).
//! 2. An UNSEEDED class's mass read is ABSENT (III.11) and the
//!    optional-bind sum is exactly `0.0`.
//! 3. The 15 cuts are monotone non-decreasing and strictly positive.
//! 4. `0.0r` or a negative cut is `E-LEX-027`.
//! 5. (I4, register row) `coefficient`'s `[0,1]` store-boundary domain
//!    (`E-EVAL-020`) already covers every `wealth-mass-*` field by virtue
//!    of its declared type — no new mechanism, cited not re-tested here.

use babylon_bsl::evaluator::Value;
use babylon_bsl::scenario::load_scenario;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_kernel::currency::Currency;
use babylon_tick::{hex, run_once};

const SCENARIO: &str = include_str!("../content/scenarios/vitality-attrition-conformance.bscn");
const RULE: &str = include_str!("../content/rules/vitality-attrition.bsl");

/// The 16 mass field qnames, rung 1 through rung 16, in declared order.
const MASS_FIELDS: [&str; 16] = [
    "social-class/wealth-mass-01",
    "social-class/wealth-mass-02",
    "social-class/wealth-mass-03",
    "social-class/wealth-mass-04",
    "social-class/wealth-mass-05",
    "social-class/wealth-mass-06",
    "social-class/wealth-mass-07",
    "social-class/wealth-mass-08",
    "social-class/wealth-mass-09",
    "social-class/wealth-mass-10",
    "social-class/wealth-mass-11",
    "social-class/wealth-mass-12",
    "social-class/wealth-mass-13",
    "social-class/wealth-mass-14",
    "social-class/wealth-mass-15",
    "social-class/wealth-mass-16",
];

/// The 15 cut defconst qnames, in declared order.
const CUT_CONSTS: [&str; 15] = [
    "wealth-sketch/cut-01",
    "wealth-sketch/cut-02",
    "wealth-sketch/cut-03",
    "wealth-sketch/cut-04",
    "wealth-sketch/cut-05",
    "wealth-sketch/cut-06",
    "wealth-sketch/cut-07",
    "wealth-sketch/cut-08",
    "wealth-sketch/cut-09",
    "wealth-sketch/cut-10",
    "wealth-sketch/cut-11",
    "wealth-sketch/cut-12",
    "wealth-sketch/cut-13",
    "wealth-sketch/cut-14",
    "wealth-sketch/cut-15",
];

/// Node ids follow scenario declaration order (`scenario.rs`: "declaration
/// order is the id order") — core=0, bourgeoisie=1, hermit=2,
/// last-worker=3, remnant=4, dissolved=5.
const CORE: u64 = 0;
const BOURGEOISIE: u64 = 1;
const HERMIT: u64 = 2;
const LAST_WORKER: u64 = 3;
const REMNANT: u64 = 4;
const DISSOLVED: u64 = 5;

/// The five classes carrying an explicit 16-value mass vector (everyone
/// except `remnant`, the absence fence's own subject).
const SEEDED_CLASSES: [(&str, u64); 5] = [
    ("core", CORE),
    ("bourgeoisie", BOURGEOISIE),
    ("hermit", HERMIT),
    ("last-worker", LAST_WORKER),
    ("dissolved", DISSOLVED),
];

fn load() -> HypergraphStore {
    let mut graph = HypergraphStore::new();
    load_scenario(SCENARIO, &mut graph).expect("the carrier scenario must load clean");
    graph
}

/// Leg 1 (§9/T4.1): every seeded class's 16 explicit mass values sum to
/// exactly `1.0` in the stored `f64` — no tolerance, matching this crate's
/// own house rule for binary64 values chosen to be exact by construction
/// (`vitality_conformance.rs`'s header explains the same discipline).
#[test]
fn every_seeded_class_reads_all_sixteen_masses_summing_to_exactly_one() {
    let graph = load();
    for (name, id) in SEEDED_CLASSES {
        let mut sum = 0.0_f64;
        for field in MASS_FIELDS {
            let value = graph
                .node_attribute(NodeId(id), field)
                .unwrap_or_else(|e| panic!("{name}: {field} must be seeded: {}", e.message));
            sum += value;
        }
        assert_eq!(sum, 1.0, "{name}: the 16 masses must sum to exactly 1.0");
    }
}

/// Leg 2 (§9/T4.1): the absence fence's own subject. `remnant` seeds NONE
/// of the 16 mass fields — every direct read is `Err` (III.11: absence is
/// a value, not a fabricated zero), and the optional-bind-style sum
/// (each absent field read as `0.0`, exactly the semantics a future
/// `:optional :default 0.0c` BSL binding would apply) is exactly `0.0` —
/// "no distribution", never a fabricated uniform (H1's own citation,
/// `content/rules/consciousness.bsl`'s UNPOSITIONED idiom).
#[test]
fn the_unseeded_class_reads_absent_and_its_optional_bind_sum_is_zero() {
    let graph = load();
    let mut sum = 0.0_f64;
    for field in MASS_FIELDS {
        let result = graph.node_attribute(NodeId(REMNANT), field);
        assert!(
            result.is_err(),
            "remnant: {field} must read ABSENT (III.11), found {result:?}"
        );
        sum += result.unwrap_or(0.0);
    }
    assert_eq!(
        sum, 0.0,
        "remnant: the optional-bind sum over 16 absent fields must be exactly 0.0"
    );
}

/// Leg 3 (§9/T4.1): the 15 cuts are strictly positive and monotone
/// non-decreasing (the check itself is `<=`, tolerating a tie even though
/// this fixture's own values happen to be strictly increasing).
#[test]
fn the_fifteen_cuts_are_strictly_positive_and_monotone_non_decreasing() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("the carrier scenario must load clean");
    let mut previous: Option<f64> = None;
    for qname in CUT_CONSTS {
        let Some(Value::Ratio { value, .. }) = loaded.consts.get(qname) else {
            panic!("{qname} must be declared as a Ratio (r-suffixed) defconst");
        };
        let cut = value.get();
        assert!(
            cut > 0.0,
            "{qname}: a cut must be strictly positive, found {cut}"
        );
        if let Some(prev) = previous {
            assert!(
                prev <= cut,
                "{qname}: the grid must be monotone non-decreasing — previous cut {prev} \
                 exceeds this one {cut}"
            );
        }
        previous = Some(cut);
    }
}

/// Leg 4 (§9/T4.1): `0.0r` is `E-LEX-027` — the reader refuses a
/// non-positive `Ratio` literal outright, so a cut of exactly zero cannot
/// even be spelled in the content language (the same gap H2′, design doc
/// §6.2, names for `cut-00`'s implicit zero convention).
///
/// **Observed, not asserted on the numeric code.** `ScenarioError`'s
/// `From<ReadError>` impl (`scenario.rs`) sets `code: None` and carries
/// only the reader's prose message — a read-time (lexer) failure never
/// propagates `LexCode::spec_code()`'s `"E-LEX-027"` string through
/// `load_scenario`'s own error type, unlike a load-time (`ScenarioError`
/// constructed directly, e.g. `E-LOAD-052`) failure, which does. This is
/// existing, pre-this-task behaviour (`reader.rs`'s own unit tests reach
/// the code via a private `lex_err` helper this integration test cannot
/// call), so the assertion below checks the reader's own stable prose
/// (`"(0, ∞)"` / `"strictly positive"`, both drawn verbatim from
/// `classify_ratio`'s doc comment and error text) rather than a code
/// string that does not, in fact, reach this boundary.
#[test]
fn a_zero_ratio_cut_literal_is_refused_at_read_time_e_lex_027() {
    let mut graph = HypergraphStore::new();
    let bad = "(scenario t/zero-cut-probe (defconst wealth-sketch/cut-01 0.0r))";
    let Err(err) = load_scenario(bad, &mut graph) else {
        panic!("a 0.0r Ratio literal must not load");
    };
    let message = err.to_string();
    assert!(
        message.contains("strictly positive") && message.contains("0, \u{221e}"),
        "the refusal must name the Ratio domain's strict-positivity law (E-LEX-027): {message}"
    );
}

/// Leg 4, the negative case — `E-LEX-027` also refuses a negative `Ratio`
/// literal, not only exactly zero. See the sibling test above for why this
/// checks the reader's prose rather than the numeric code string.
#[test]
fn a_negative_ratio_cut_literal_is_refused_at_read_time_e_lex_027() {
    let mut graph = HypergraphStore::new();
    let bad = "(scenario t/negative-cut-probe (defconst wealth-sketch/cut-01 -1r))";
    let Err(err) = load_scenario(bad, &mut graph) else {
        panic!("a -1r Ratio literal must not load");
    };
    let message = err.to_string();
    assert!(
        message.contains("strictly positive") && message.contains("0, \u{221e}"),
        "the refusal must name the Ratio domain's strict-positivity law (E-LEX-027): {message}"
    );
}

/// `η` (household-person-equivalence, DP-7 = A) and `τ`
/// (subsistence-horizon, DP-5 = A now) ship at their RULED values —
/// reconciliation record §3.2/§4.3, sitting posted on #491,
/// 2026-08-18T02:42:38Z.
#[test]
fn household_person_equivalence_and_subsistence_horizon_are_declared_at_their_ruled_values() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("the carrier scenario must load clean");
    let Some(Value::Ratio { value: eta, .. }) = loaded
        .consts
        .get("wealth-sketch/household-person-equivalence")
    else {
        panic!("household-person-equivalence must be declared as a Ratio defconst");
    };
    assert_eq!(
        eta.get(),
        1.0,
        "DP-7 = A: eta ships at the declared identity value"
    );

    let Some(Value::Ratio { value: tau, .. }) = loaded.consts.get("vitality/subsistence-horizon")
    else {
        panic!("subsistence-horizon must be declared as a Ratio defconst");
    };
    assert_eq!(
        tau.get(),
        1.0,
        "DP-5 = A now: tau ships at the definitional value"
    );
}

/// The Currency lane (T3, OQ-J): `wealth`/`s-bio`/`s-class` round-trip
/// through the typed `i128` micro-unit storage exactly, on both a
/// multi-member and a one-member class.
#[test]
fn currency_lane_fields_round_trip_exactly() {
    let graph = load();
    assert_eq!(
        graph
            .node_attribute_currency(NodeId(CORE), "social-class/wealth")
            .expect("core: wealth must be a currency field"),
        Currency::from_micro_units(1_000 * 1_000_000)
    );
    assert_eq!(
        graph
            .node_attribute_currency(NodeId(BOURGEOISIE), "social-class/s-class")
            .expect("bourgeoisie: s-class must be a currency field"),
        Currency::from_micro_units(8 * 1_000_000)
    );
    assert_eq!(
        graph
            .node_attribute_currency(NodeId(LAST_WORKER), "social-class/wealth")
            .expect("last-worker: wealth must be a currency field"),
        Currency::from_micro_units(1_000_000)
    );
}

/// Byte-determinism, the same discipline every other pin in this crate
/// carries: two runs, one post-state hash. `fired == 0` and
/// `before == after` are the load-only probe's own expected result, not
/// an oversight — see the probe rule's own header.
#[test]
fn the_carrier_tick_is_deterministic_and_the_probe_never_fires() {
    let a = run_once(SCENARIO, RULE).expect("first run");
    let b = run_once(SCENARIO, RULE).expect("second run");
    assert_eq!(a.after, b.after, "two runs, one post-state");
    assert_eq!(
        hex(&a.before),
        hex(&a.after),
        "the never-firing probe must leave the graph untouched"
    );
    assert_eq!(
        a.fired, 0,
        "the probe's guard is false for every legal population"
    );
}
