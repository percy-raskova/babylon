//! Posture suite for the K=16 wealth-mass carrier (#491 T4, Phase 1 —
//! "the carrier, inert"; design doc §6.2 H1; ADR194 R1) **plus** the T5
//! (Phase 3a) conformance suite for its first real consumer,
//! `vitality/subsistence-clearing` — the dual measure `clearing`/
//! `failing_certain`/`straddle_band` (H2', design doc §6.2; ADR173's
//! P(S|A)).
//!
//! # What this file is, and is not
//!
//! `content/scenarios/vitality-attrition-conformance.bscn` declares and
//! seeds the carrier — sixteen per-class wealth-mass shares, the fifteen
//! grid cuts, the household→person crossing (`η`), and the subsistence
//! horizon (`τ`). T4's own load-time posture tests below (unchanged)
//! still read those raw substrate facts directly through
//! [`babylon_graph::substrate::GraphSubstrate`], never through a rule's
//! binding machinery — Phase 1 supplies the carrier, not the derivation
//! (design doc §12 item 1). **T5 gives the carrier its first real rule**
//! (`content/rules/vitality-attrition.bsl`, replacing the never-firing
//! probe): it fires for the four classes whose guard admits them (core,
//! bourgeoisie, hermit, last-worker), and its ONLY observable channel is
//! `emit` — no `update-node`/`update-edge`/`update-hyperedge` verb
//! appears anywhere in the rule, so the K=16 carrier's own state-hash pin
//! stays byte-identical to T4's measurement even though the rule now
//! fires for real (T5.7: "a binding and a condition, no effect"). The
//! measure-arithmetic tests below therefore read `sink.events`, not
//! post-tick graph state.
//!
//! # File deviation, disclosed (beyond the brief's own "Files:" line)
//!
//! The task brief's own "Files:" line (transcribed verbatim from the
//! plan, `docs/superpowers/plans/2026-08-17-491-rung-ladder.md:1293`)
//! names `content/rules/vitality.bsl` as T5's rule target. That file
//! cannot host `vitality/subsistence-clearing`: it is loaded VERBATIM by
//! `vitality_conformance.rs`'s and `tick_goldens.rs`'s PINNED tests
//! together with `vitality-conformance.bscn`, which declares none of the
//! sixteen `wealth-mass-*` fields, the fifteen `cut-*` defconsts, or
//! `vitality/subsistence-horizon` — an undeclared qname is `E-LOAD-010`
//! UNCONDITIONALLY (`bindings.rs:220`, `:optional` or not), so landing
//! this rule there would break all eighteen pre-existing pins AT LOAD,
//! not drift them. `vitality-attrition.bsl` (this file's own `RULE`
//! const, unchanged path) already declares every construct this rule
//! reads, and its own T4 header already named itself as what "a future
//! task may extend in place or replace outright." See the rule file's own
//! header for the full citation chain.
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
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_kernel::currency::Currency;
use babylon_tick::{hex, run_once, run_once_into};

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
/// carries: two runs, one post-state hash. `before == after` still holds
/// post-T5 — NOT because the rule never fires (it fires for four of the
/// six classes now), but because its only effect is `emit`, which never
/// touches graph state (III.11: `update-node`/`update-edge`/
/// `update-hyperedge`/`add-*`/`remove-*` never appear in
/// `vitality/subsistence-clearing`). `fired == 4` is `core`,
/// `bourgeoisie`, `hermit`, `last-worker` — `remnant` (mass-sum guard, all
/// sixteen masses absent) and `dissolved` (`active = 0`) are excluded;
/// see `the_unseeded_class_produces_no_reading_and_the_rule_does_not_fire`
/// below for the absence-fence leg this number stands on.
#[test]
fn the_carrier_tick_is_deterministic_and_the_measure_rule_fires_for_four_of_six_classes() {
    let a = run_once(SCENARIO, RULE).expect("first run");
    let b = run_once(SCENARIO, RULE).expect("second run");
    assert_eq!(a.after, b.after, "two runs, one post-state");
    assert_eq!(
        hex(&a.before),
        hex(&a.after),
        "emit is the rule's only effect — it never mutates graph state"
    );
    assert_eq!(
        a.fired, 4,
        "core, bourgeoisie, hermit, last-worker pass the guard; remnant \
         (mass-sum = 0) and dissolved (active = 0) do not"
    );
}

// ============================================================================
// T5 (#491, Phase 3a) — the dual measure conformance suite.
//
// `vitality/subsistence-clearing`'s own `:material-basis` and header carry
// the full derivation (H2', the S-7 derivation, the H3 horizon identity,
// the ADR210 R13 level-set citation). This suite verifies FOUR vector
// families (design doc §9/T5.1): (1) measure arithmetic against the
// independent Python oracle, exact equality; (2) boundary conditions; (3)
// monotonicity properties, including ADR202 R2's asserted sign; (4) the
// absence fence.
// ============================================================================

/// The fifteen grid cuts, the SAME values `vitality-attrition-
/// conformance.bscn` declares as `wealth-sketch/cut-01`..`-15` — mirrored
/// here (not read from the scenario) because the boundary/property tests
/// below construct SYNTHETIC `(masses, w_bar, s_stock)` triples the
/// fixture's own four firing classes cannot reach (their ratios are fixed
/// by the scenario).
const SYNTHETIC_CUTS: [f64; 15] = [
    0.18, 0.25, 0.32, 0.40, 0.50, 0.62, 0.75, 0.90, 1.05, 1.22, 1.40, 1.60, 1.85, 2.15, 2.50,
];

/// Mirrors `vitality/subsistence-clearing`'s own STEP algebra exactly
/// (H2', design doc §6.2 — `clearing`'s rungs 2..16 against `cut_{k-1}`,
/// `failing_certain`'s rungs 1..15 against `cut_k`, `>=`-inclusive on the
/// clearing side, strict `<` on the failing side, `straddle_band` the
/// complement against `mass_sum` — review I-1, matching the rule's own
/// `(- mass-sum (+ clearing failing-certain))`, never a stipulated
/// `1.0`). NOT a competing third implementation: it is the rule's OWN
/// closed form, transcribed so the boundary/property/dispersion-sign
/// families below can sweep threshold ratios the fixture's four firing
/// classes do not reach, at a sample density (dozens of points) a real
/// BSL tick per point cannot practically provide. **A transcription
/// error here cannot be caught by this file alone** — review I-3's own
/// finding — which is why `evaluator_reaches_an_exact_cut_boundary_and_a_genuine_straddle`
/// below runs these SAME boundary/straddle claims through the actual
/// evaluator (a scratch scenario + `run_once_into`), independently of
/// this function.
fn clearing_failing_straddle(
    masses: &[f64; 16],
    cuts: &[f64; 15],
    w_bar: f64,
    s_stock: f64,
) -> (f64, f64, f64) {
    let mass_sum: f64 = masses.iter().sum();
    let edges: Vec<f64> = cuts.iter().map(|c| c * w_bar).collect();
    let mut clearing = 0.0_f64;
    for k in 2..=16_usize {
        if edges[k - 2] >= s_stock {
            clearing += masses[k - 1];
        }
    }
    let mut failing_certain = 0.0_f64;
    for k in 1..=15_usize {
        if edges[k - 1] < s_stock {
            failing_certain += masses[k - 1];
        }
    }
    let straddle_band = mass_sum - clearing - failing_certain;
    (clearing, failing_certain, straddle_band)
}

/// Family (1), Measure arithmetic (T5.1(1)) — expected values from the
/// independent Python oracle
/// (`content/scenarios/vitality_attrition_conformance.py`), **exact
/// equality, no tolerance**. Provenance: `PYTHONPATH="$PWD/src" uv run
/// python rust/crates/babylon-tick/content/scenarios/
/// vitality_attrition_conformance.py` (no `PYTHONPATH` actually needed —
/// the oracle imports nothing from `babylon.*`, ADR183/ADR173, see its own
/// header), output on 2026-08-18, verbatim:
///
/// ```text
/// measure vectors (S = s_bio + s_class, ADR210 R13 acquiescence level set; tau=1.0):
///   core         w_bar=10.0 s_stock=2.0 clearing=1.0 failing_certain=0.0 straddle_band=0.0
///   bourgeoisie  w_bar=125.0 s_stock=10.0 clearing=1.0 failing_certain=0.0 straddle_band=0.0
///   hermit       w_bar=100.0 s_stock=2.0 clearing=1.0 failing_certain=0.0 straddle_band=0.0
///   last-worker  w_bar=1.0 s_stock=2.0 clearing=0.0 failing_certain=1.0 straddle_band=0.0
/// ```
///
/// Both sides run IEEE-754 basic operations on binary64 — the same
/// exact-equality discipline `vitality_conformance.rs`'s own header
/// documents (`+ − × ÷` and comparison, correctly rounded, reproducing
/// bit-exactly across implementations, `bsl-language.rst` §4.3); a
/// tolerance here would hide exactly the transcription error it would
/// appear to absorb.
#[test]
fn measure_arithmetic_matches_the_independent_oracle_exactly() {
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(SCENARIO, RULE, &mut graph, &mut sink).expect("the measure rule must run");

    assert_eq!(
        sink.events.len(),
        4,
        "exactly the four guard-admitted classes"
    );
    for (event_type, _) in &sink.events {
        assert_eq!(event_type, "SUBSISTENCE_CLEARANCE_MEASURED");
    }

    // (node id, w_bar $, s_stock $, mass_sum, clearing, failing_certain, straddle_band)
    let expected: [(u64, i128, i128, f64, f64, f64, f64); 4] = [
        (CORE, 10 * 1_000_000, 2 * 1_000_000, 1.0, 1.0, 0.0, 0.0),
        (
            BOURGEOISIE,
            125 * 1_000_000,
            10 * 1_000_000,
            1.0,
            1.0,
            0.0,
            0.0,
        ),
        (HERMIT, 100 * 1_000_000, 2 * 1_000_000, 1.0, 1.0, 0.0, 0.0),
        (LAST_WORKER, 1_000_000, 2 * 1_000_000, 1.0, 0.0, 1.0, 0.0),
    ];
    for (i, (id, w_bar_micro, s_stock_micro, mass_sum, clearing, failing_certain, straddle_band)) in
        expected.into_iter().enumerate()
    {
        let payload = &sink.events[i].1;
        let expected_payload = vec![
            ("entity-id".to_owned(), Value::NodeRef(NodeId(id))),
            (
                "w-bar".to_owned(),
                Value::Currency(Currency::from_micro_units(w_bar_micro)),
            ),
            (
                "s-stock".to_owned(),
                Value::Currency(Currency::from_micro_units(s_stock_micro)),
            ),
            ("mass-sum".to_owned(), Value::Real(mass_sum)),
            ("clearing".to_owned(), Value::Real(clearing)),
            ("failing-certain".to_owned(), Value::Real(failing_certain)),
            ("straddle-band".to_owned(), Value::Real(straddle_band)),
        ];
        assert_eq!(payload, &expected_payload, "measurement {i} (node {id})");
        // Review I-1: assert the identity against the EMITTED mass-sum, not
        // a hardcoded 1.0 — a partially-seeded class's short mass-sum would
        // be visible here (the identity would still hold, at a total below
        // 1.0), rather than absorbed into a fabricated straddle-band.
        let emitted_mass_sum = match &payload[3] {
            (label, Value::Real(v)) if label == "mass-sum" => *v,
            other => panic!("expected mass-sum at payload position 3, found {other:?}"),
        };
        assert_eq!(
            clearing + failing_certain + straddle_band,
            emitted_mass_sum,
            "the dual-plus-straddle identity against the EMITTED mass-sum, node {id}"
        );
    }
}

/// Family (2), Boundary (T5.1(2)). `S·τ` below every cut: `clearing = 1 −
/// mass-01` (STEP, rung 1 excluded by construction) and
/// `failing_certain = 0`.
#[test]
fn boundary_s_tau_below_every_cut() {
    // 0.25/0.75 (exact dyadic fractions in binary64) — this crate's own
    // house rule for a hand-authored fixture whose sum must be exact, no
    // rounding artifact from the fixture's OWN chosen values (T4's own
    // `vitality_attrition_conformance.rs` header states the identical
    // discipline).
    let mut masses = [0.0_f64; 16];
    masses[0] = 0.25; // rung 1 — never counted toward clearing
    masses[7] = 0.75; // rung 8
    let w_bar = 1.0;
    let s_stock = 0.10; // below cut-01 * w_bar = 0.18
    let (clearing, failing_certain, straddle_band) =
        clearing_failing_straddle(&masses, &SYNTHETIC_CUTS, w_bar, s_stock);
    assert_eq!(
        clearing,
        1.0 - masses[0],
        "clearing = 1 - mass-01 under STEP"
    );
    assert_eq!(failing_certain, 0.0);
    assert_eq!(straddle_band, masses[0]);
}

/// Family (2), Boundary. `S·τ` at/above every cut: `clearing = 0`.
#[test]
fn boundary_s_tau_at_or_above_every_cut() {
    let mut masses = [0.0_f64; 16];
    masses[0] = 0.25;
    masses[7] = 0.75;
    let w_bar = 1.0;
    let s_stock = 3.0; // above cut-15 * w_bar = 2.50
    let (clearing, failing_certain, straddle_band) =
        clearing_failing_straddle(&masses, &SYNTHETIC_CUTS, w_bar, s_stock);
    assert_eq!(clearing, 0.0, "no rung's lower edge reaches s_stock");
    assert_eq!(
        failing_certain, 1.0,
        "every rung 1..15's upper edge falls short"
    );
    assert_eq!(straddle_band, 0.0);
}

/// Family (2), Boundary. Exactly on a cut — `≥`-inclusive (M-4: a
/// comparison has no rounding mode). `s_stock` sits at EXACTLY
/// `cut-08 * w_bar`: rung 9's lower edge is `cut-08`, so rung 9 clears
/// (`>=`, inclusive); rung 8's upper edge is ALSO `cut-08`, so rung 8 does
/// NOT certainly fail (`<` is strict) — its mass becomes the straddle
/// band, demonstrating both the inclusive boundary and the straddle
/// mechanism at once. 0.5/0.5 (exact in binary64), the same house rule
/// the sibling boundary tests above use.
#[test]
fn boundary_exactly_on_a_cut_is_inclusive_on_the_clearing_side() {
    let mut masses = [0.0_f64; 16];
    masses[7] = 0.5; // rung 8 — straddles
    masses[8] = 0.5; // rung 9 — clears (inclusive lower edge)
    let w_bar = 1.0;
    let s_stock = SYNTHETIC_CUTS[7]; // cut-08 exactly, * w_bar = 0.90
    let (clearing, failing_certain, straddle_band) =
        clearing_failing_straddle(&masses, &SYNTHETIC_CUTS, w_bar, s_stock);
    assert_eq!(clearing, 0.5, "rung 9 clears at the inclusive boundary");
    assert_eq!(
        failing_certain, 0.0,
        "rung 8 does not CERTAINLY fail — < is strict"
    );
    assert_eq!(straddle_band, 0.5, "rung 8's mass is the straddled band");
}

/// Family (3), Property (T5.1(3)). `clearing` is non-increasing in `S`
/// (holding `w_bar` fixed) and non-decreasing in `w_bar` (holding `S`
/// fixed) — the S-7 derivation's own claim that `clearing` is a
/// complementary CDF, never a curve that can rise as the threshold rises
/// or fall as wealth rises.
#[test]
fn clearing_is_monotone_in_s_and_in_w_bar() {
    let mut masses = [0.0_f64; 16];
    for m in &mut masses {
        *m = 1.0 / 16.0;
    }
    let w_bar = 1.0;
    let s_stocks: Vec<f64> = (0..40).map(|i| 0.05 + f64::from(i) * 0.08).collect();
    let clearings: Vec<f64> = s_stocks
        .iter()
        .map(|&s| clearing_failing_straddle(&masses, &SYNTHETIC_CUTS, w_bar, s).0)
        .collect();
    for pair in clearings.windows(2) {
        assert!(
            pair[1] <= pair[0] + f64::EPSILON,
            "clearing must be non-increasing in S: {pair:?}"
        );
    }

    let s_stock = 1.0;
    let w_bars: Vec<f64> = (1..40).map(f64::from).collect();
    let clearings_w: Vec<f64> = w_bars
        .iter()
        .map(|&w| clearing_failing_straddle(&masses, &SYNTHETIC_CUTS, w, s_stock).0)
        .collect();
    for pair in clearings_w.windows(2) {
        assert!(
            pair[1] >= pair[0] - f64::EPSILON,
            "clearing must be non-decreasing in w_bar: {pair:?}"
        );
    }
}

/// Family (3), Property. ADR202 R2's asserted sign — more intra-class
/// dispersion implies LESS switch-like rupture — **tested HERE ONLY, in
/// this hand-authored fixture, where masses are free** (design doc
/// §9/T5.1(3)).
///
/// **Limitation, stated explicitly (C-6):** in the seeded world A2 gives
/// one shape per county shared by every class, so intra-class dispersion
/// is a county constant and this sign has no class-varying degrees of
/// freedom to be right or wrong about there. The real-data companion is
/// T8a.6; the honest claim is that R2 is CARRIED, not satisfied, by this
/// train (DP-10).
///
/// The proxy for "switch-like": the LARGEST single-step drop in
/// `clearing` across a threshold sweep spanning every cut. A concentrated
/// distribution (all mass in one rung) drops its entire mass in one step
/// when the sweep crosses that rung's boundary — maximally switch-like. A
/// dispersed distribution (mass spread across every rung) sheds a little
/// mass at every boundary — no single step is large.
#[test]
fn adr202_r2_more_dispersion_means_a_less_switch_like_transition() {
    let mut concentrated = [0.0_f64; 16];
    concentrated[7] = 1.0; // all mass in rung 8

    let mut dispersed = [0.0_f64; 16];
    for m in &mut dispersed {
        *m = 1.0 / 16.0; // mass spread evenly across every rung
    }

    let w_bar = 1.0;
    // One sample strictly between every consecutive pair of cuts, plus one
    // below cut-01 and one above cut-15 — sixteen points spanning the
    // whole grid, so a sweep step can land on every rung boundary.
    let mut sweep: Vec<f64> = vec![SYNTHETIC_CUTS[0] - 0.05];
    for pair in SYNTHETIC_CUTS.windows(2) {
        sweep.push((pair[0] + pair[1]) / 2.0);
    }
    sweep.push(SYNTHETIC_CUTS[14] + 0.05);

    let max_step = |masses: &[f64; 16]| -> f64 {
        let clearings: Vec<f64> = sweep
            .iter()
            .map(|&s| clearing_failing_straddle(masses, &SYNTHETIC_CUTS, w_bar, s).0)
            .collect();
        clearings
            .windows(2)
            .map(|p| (p[0] - p[1]).abs())
            .fold(0.0_f64, f64::max)
    };

    let concentrated_max_step = max_step(&concentrated);
    let dispersed_max_step = max_step(&dispersed);
    assert_eq!(
        concentrated_max_step, 1.0,
        "the concentrated fixture sheds its entire mass in one sweep step"
    );
    assert!(
        concentrated_max_step > dispersed_max_step,
        "R2's sign: more dispersion ({dispersed_max_step}) means a LESS \
         switch-like transition than concentration ({concentrated_max_step})"
    );
}

/// Family (4), Absence (T5.1(4)). The unseeded class produces NO reading
/// and the guarded rule does not fire: `remnant` (id 4) never appears
/// among the emitted events, even though it is `active = 1` with
/// `population = 1` — the sum-guard (H1's own citation, the UNPOSITIONED
/// idiom) excludes it on `mass-sum = 0` alone, distinct from `dissolved`'s
/// pre-existing `active = 0` exclusion.
#[test]
fn the_unseeded_class_produces_no_reading_and_the_rule_does_not_fire() {
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(SCENARIO, RULE, &mut graph, &mut sink).expect("the measure rule must run");

    let fired_ids: Vec<NodeId> = sink
        .events
        .iter()
        .map(|(_, payload)| match payload.first() {
            Some((label, Value::NodeRef(id))) if label == "entity-id" => *id,
            other => panic!("expected an entity-id NodeRef payload item first, found {other:?}"),
        })
        .collect();
    assert!(
        !fired_ids.contains(&NodeId(REMNANT)),
        "remnant must produce no reading: {fired_ids:?}"
    );
    assert!(
        !fired_ids.contains(&NodeId(DISSOLVED)),
        "dissolved must produce no reading: {fired_ids:?}"
    );
    assert_eq!(
        fired_ids.len(),
        4,
        "core, bourgeoisie, hermit, last-worker only"
    );
}

// ============================================================================
// Fix round 1 (task-5-review.md, findings I-1/I-2/I-3): the two tests below
// run ENGINEERED scratch scenarios through the real evaluator. Neither
// touches `vitality-attrition-conformance.bscn` — its own T4 pin would
// move (design doc §5.4 item 5) — so both build a minimal, throwaway
// `.bscn` string instead, the same discipline this file's own
// `a_zero_ratio_cut_literal_is_refused_at_read_time_e_lex_027` test already
// uses.
// ============================================================================

/// One scratch-scenario node: `(name, active, population, wealth$, s_bio$,
/// s_class$, masses)` — all-integer Currency amounts, so no
/// literal-formatting risk.
type ScratchNode<'a> = (&'a str, i64, i64, i64, i64, i64, [f64; 16]);

/// Builds a minimal scratch scenario declaring exactly the constructs
/// `vitality/subsistence-clearing` reads, with one `NodeType/SOCIAL_CLASS`
/// node per [`ScratchNode`]. Cuts are the SAME fifteen values as the
/// committed carrier (`SYNTHETIC_CUTS`) and `tau` is the same ruled
/// `1.0r`, so a hand-derived expected vector transfers directly. Only
/// NONZERO masses are written — the rest ride the rule's own `:optional
/// :default 0.0c` idiom, exercising the absence fence here too.
fn scratch_scenario(nodes: &[ScratchNode<'_>]) -> String {
    let mut s = String::from("(scenario t/subsistence-clearing-probe\n");
    s.push_str("  (deffield social-class/active int extensive)\n");
    s.push_str("  (deffield social-class/population int extensive)\n");
    s.push_str("  (deffield social-class/wealth currency extensive)\n");
    s.push_str("  (deffield social-class/s-bio currency intensive)\n");
    s.push_str("  (deffield social-class/s-class currency intensive)\n");
    for field in MASS_FIELDS {
        s.push_str(&format!("  (deffield {field} coefficient intensive)\n"));
    }
    for (i, qname) in CUT_CONSTS.iter().enumerate() {
        s.push_str(&format!("  (defconst {qname} {:?}r)\n", SYNTHETIC_CUTS[i]));
    }
    s.push_str("  (defconst vitality/subsistence-horizon 1.0r)\n");
    for (name, active, population, wealth, s_bio, s_class, masses) in nodes {
        s.push_str(&format!(
            "  (node {name} NodeType/SOCIAL_CLASS\n    \
             (social-class/active {active})\n    \
             (social-class/population {population})\n    \
             (social-class/wealth {wealth}$)\n    \
             (social-class/s-bio {s_bio}$)\n    \
             (social-class/s-class {s_class}$)\n"
        ));
        for (i, field) in MASS_FIELDS.iter().enumerate() {
            if masses[i] != 0.0 {
                s.push_str(&format!("    ({field} {:?}c)\n", masses[i]));
            }
        }
        s.push_str("  )\n");
    }
    s.push_str(")\n");
    s
}

/// Review I-2: `:expr` bindings resolve for EVERY subject BEFORE the
/// `when` guard runs (`tick.rs`'s `collect_pass` order — bindings first,
/// guard second), so an UNGUARDED `(/ wealth population-int)` would abort
/// the WHOLE TICK for a `population = 0` class (`E-EVAL-012`, division by
/// zero) even though the guard's own `(> population 0)` would have
/// excluded that class from firing — the guard never gets a chance to
/// run. A negative population trips `floor`'s own `E-EVAL-039` one step
/// earlier. The fix nests `if` around both `population-int` and `w-bar`
/// (never a clamp), making both bindings TOTAL. This proves the tick
/// SURVIVES both cases and that neither class fires.
#[test]
fn a_zero_or_negative_population_class_does_not_abort_the_tick() {
    let scenario = scratch_scenario(&[
        ("zero-pop", 1, 0, 100, 1, 1, [0.0_f64; 16]),
        ("negative-pop", 1, -1, 100, 1, 1, [0.0_f64; 16]),
    ]);
    let report = run_once(&scenario, RULE).expect(
        "population <= 0 must not abort the tick — population-int/w-bar are now total functions",
    );
    assert_eq!(
        report.fired, 0,
        "neither class passes the guard's (> population 0)"
    );
}

/// Review I-3: every boundary/property/dispersion-sign test above runs a
/// Rust TRANSCRIPTION of the rule (`clearing_failing_straddle`), and the
/// only four vectors that reach the real evaluator
/// (`measure_arithmetic_matches_the_independent_oracle_exactly`) are all
/// degenerate — `clearing`/`failing_certain` each land in `{0, 1}` and
/// `straddle_band` is always exactly `0` for the committed fixture's four
/// firing classes — so a mutation that flipped every `>=` to `>` in the
/// rule would leave every prior test green (verified: see this test's own
/// closing mutation check). This test runs the SAME two boundary claims
/// through the REAL evaluator via an engineered scratch scenario.
///
/// `on-cut`: `w_bar = $10`, `s_stock = $9 = cut-08 * w_bar` EXACTLY — the
/// `>=`-inclusive boundary law (M-4, "a comparison has no rounding mode").
/// `mass-08 = 0.5` straddles (its own upper edge, `cut-08`, is NOT
/// strictly less than `s_stock`, so it does not certainly fail either);
/// `mass-09 = 0.5` clears (its lower edge is ALSO `cut-08`, `>=` inclusive).
///
/// `off-cut`: `w_bar = $10`, `s_stock = $3`, strictly between
/// `cut-02 * w_bar = $2.5` and `cut-03 * w_bar = $3.2` — a GENUINE
/// straddle with no cut coincidence. `mass-01 = 0.125` fails;
/// `mass-03 = 0.625` straddles; `mass-16 = 0.25` clears — exact dyadic
/// fractions (binary64-exact, this crate's own house rule for a
/// hand-authored fixture whose sum must be exact, `1/8 + 5/8 + 2/8 = 1`).
///
/// Hand-derived (not oracle-transcribed — the Python oracle's own
/// `SUBJECTS` list is the committed fixture only), then cross-checked
/// against `clearing_failing_straddle` BEFORE the rule ever runs, so a
/// disagreement between the hand derivation and the Rust mirror is caught
/// here rather than the two implementations sharing one blind spot.
#[test]
fn evaluator_reaches_an_exact_cut_boundary_and_a_genuine_straddle() {
    let mut on_cut_masses = [0.0_f64; 16];
    on_cut_masses[7] = 0.5; // rung 8 -- straddles
    on_cut_masses[8] = 0.5; // rung 9 -- clears at the inclusive boundary

    let mut off_cut_masses = [0.0_f64; 16];
    off_cut_masses[0] = 0.125; // rung 1 -- fails
    off_cut_masses[2] = 0.625; // rung 3 -- straddles, no cut coincidence
    off_cut_masses[15] = 0.25; // rung 16 -- clears

    let (on_cut_clearing, on_cut_failing, on_cut_straddle) =
        clearing_failing_straddle(&on_cut_masses, &SYNTHETIC_CUTS, 10.0, 9.0);
    assert_eq!(
        (on_cut_clearing, on_cut_failing, on_cut_straddle),
        (0.5, 0.0, 0.5),
        "hand derivation vs. the Rust mirror must agree before the rule ever runs"
    );
    let (off_cut_clearing, off_cut_failing, off_cut_straddle) =
        clearing_failing_straddle(&off_cut_masses, &SYNTHETIC_CUTS, 10.0, 3.0);
    assert_eq!(
        (off_cut_clearing, off_cut_failing, off_cut_straddle),
        (0.25, 0.125, 0.625),
        "hand derivation vs. the Rust mirror must agree before the rule ever runs"
    );

    let scenario = scratch_scenario(&[
        ("on-cut", 1, 1, 10, 1, 8, on_cut_masses),
        ("off-cut", 1, 1, 10, 1, 2, off_cut_masses),
    ]);

    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(&scenario, RULE, &mut graph, &mut sink)
        .expect("the engineered scratch scenario must tick clean");
    assert_eq!(
        sink.events.len(),
        2,
        "both engineered classes pass the guard"
    );

    let s_stock_micro: [i128; 2] = [9 * 1_000_000, 3 * 1_000_000];
    let expected: [(u64, f64, f64, f64); 2] = [
        (0, on_cut_clearing, on_cut_failing, on_cut_straddle),
        (1, off_cut_clearing, off_cut_failing, off_cut_straddle),
    ];
    for (i, (id, clearing, failing_certain, straddle_band)) in expected.into_iter().enumerate() {
        let payload = &sink.events[i].1;
        let expected_payload = vec![
            ("entity-id".to_owned(), Value::NodeRef(NodeId(id))),
            (
                "w-bar".to_owned(),
                Value::Currency(Currency::from_micro_units(10 * 1_000_000)),
            ),
            (
                "s-stock".to_owned(),
                Value::Currency(Currency::from_micro_units(s_stock_micro[i])),
            ),
            ("mass-sum".to_owned(), Value::Real(1.0)),
            ("clearing".to_owned(), Value::Real(clearing)),
            ("failing-certain".to_owned(), Value::Real(failing_certain)),
            ("straddle-band".to_owned(), Value::Real(straddle_band)),
        ];
        assert_eq!(
            payload, &expected_payload,
            "engineered class {i} (node {id})"
        );
    }
}
