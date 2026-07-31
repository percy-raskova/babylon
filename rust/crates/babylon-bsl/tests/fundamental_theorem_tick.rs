//! **P27 Phase 2 Slice 1: the vertical slice, end to end.**
//!
//! Scenario file → world → loaded rule → tick → deterministic state hash.
//! Every stage is the real one; nothing here is a stub.
//!
//! This exists because until it passed, the Rust engine could parse a rule
//! and hold a graph but could not *run* anything: there was no world-load
//! path and no loop to drive rules over a population. "We have a language"
//! becomes "we have an engine" at the point this file goes green.
//!
//! # The rule under test
//!
//! The Fundamental Theorem: revolution in the core is impossible while wages
//! exceed the value produced, and the gap is imperial rent (Φ). Chosen as the
//! first rule because it is the theoretical spine every other mechanic hangs
//! off, and because it has the minimum shape a real rule needs — read
//! attributes, compare, write a derived value back.
//!
//! The scenario carries two classes drawn to make the theorem's *two* cases
//! visible in one tick, which is the point of the test:
//!
//! - a **core** class with wages 120 against value produced 80 — extracting
//!   Φ = 40, the labour-aristocracy position;
//! - a **periphery** class with wages 20 against value produced 90 — the
//!   guard is false, nothing is written, and the absence of an
//!   `imperial-rent` attribute on that node is itself the assertion.
//!
//! A rule that fired on everything would pass a weaker test. The periphery
//! class is here so the guard has to actually discriminate.

use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::EmptyIntrinsicHost;
use babylon_bsl::rule_pipeline::{load_rule, LoadContext};
use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::run_tick;
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::{BslType, FieldDecl, FieldKind};
use babylon_bsl::BindingVocabulary;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use std::collections::{HashMap, HashSet};

const SCENARIO: &str = r"
(scenario ft/two-classes
  (deffield social-class/wages int extensive)
  (deffield social-class/value-produced int extensive)
  (deffield social-class/imperial-rent int extensive)
  (node core NodeType/SOCIAL_CLASS
    (social-class/wages 120)
    (social-class/value-produced 80))
  (node periphery NodeType/SOCIAL_CLASS
    (social-class/wages 20)
    (social-class/value-produced 90)))
";

const FUNDAMENTAL_THEOREM: &str = r#"
(rule economics/fundamental-theorem
  :material-basis "core wages above the value core labour produces is imperial rent; while the gap holds, revolution in the core is materially foreclosed"
  :fuel 64
  (bindings
    (binding wages :field social-class/wages)
    (binding value-produced :field social-class/value-produced))
  (when (> wages value-produced))
  (effects
    (update-node self social-class/imperial-rent (set (- wages value-produced)))))
"#;

fn field(ty: BslType, kind: FieldKind) -> FieldDecl {
    FieldDecl { ty, kind }
}

fn types() -> TypeEnv {
    TypeEnv {
        fields: HashMap::from([
            (
                "social-class/wages".to_owned(),
                field(BslType::Int, FieldKind::Extensive),
            ),
            (
                "social-class/value-produced".to_owned(),
                field(BslType::Int, FieldKind::Extensive),
            ),
            (
                "social-class/imperial-rent".to_owned(),
                field(BslType::Int, FieldKind::Extensive),
            ),
        ]),
        exemptions: &[],
    }
}

struct Registries {
    vocabulary: BindingVocabulary,
    types: TypeEnv,
    ceilings: CardinalityCeilings,
    intrinsics: IntrinsicCosts,
    systems: HashSet<String>,
}

fn registries() -> Registries {
    let declared = types();
    Registries {
        vocabulary: BindingVocabulary {
            fields: declared.fields.keys().cloned().collect(),
            consts: HashSet::new(),
            metrics: HashSet::new(),
        },
        types: declared,
        ceilings: CardinalityCeilings::new(
            HashMap::from([("NodeType/SOCIAL_CLASS".to_owned(), 100)]),
            HashMap::new(),
        ),
        intrinsics: IntrinsicCosts::default(),
        systems: HashSet::from(["economics".to_owned()]),
    }
}

/// The whole slice: load a world, load a rule, run one tick.
fn run_one_tick() -> (MemoryGraph, usize, usize) {
    let r = registries();
    let mut graph = MemoryGraph::new();
    load_scenario(SCENARIO, &mut graph).expect("the scenario must load");

    let ctx = LoadContext {
        vocabulary: &r.vocabulary,
        types: &r.types,
        ceilings: &r.ceilings,
        intrinsics: &r.intrinsics,
        systems: &r.systems,
        rule_file: "economics/fundamental-theorem.bsl",
    };
    let loaded = load_rule(FUNDAMENTAL_THEOREM, &ctx).expect("the rule must pass every load gate");

    let mut sink = CollectingSink::default();
    let outcome = run_tick(
        &loaded,
        &r.types,
        &EmptyIntrinsicHost,
        &mut graph,
        &mut sink,
        &r.intrinsics,
    )
    .expect("the tick must run");

    (graph, outcome.considered, outcome.fired)
}

#[test]
fn the_fundamental_theorem_runs_end_to_end() {
    let (graph, considered, fired) = run_one_tick();

    assert_eq!(considered, 2, "both classes were subjects");
    assert_eq!(fired, 1, "the guard discriminated — only the core extracts");

    // The core class: Φ = 120 − 80 = 40, written back to the graph.
    let rent = graph
        .node_attribute(NodeId(0), "social-class/imperial-rent")
        .expect("the core class must carry its imperial rent");
    assert!(
        (rent - 40.0).abs() < 1e-12,
        "Φ = wages − value produced = 40, got {rent}"
    );
}

#[test]
fn the_periphery_carries_no_rent_and_that_absence_is_the_assertion() {
    // III.11: a class that extracts nothing has NO imperial-rent attribute —
    // not a zero. A stored 0.0 would be a claim ("measured, and it is none");
    // the absence is the honest state ("this class does not extract").
    let (graph, _, _) = run_one_tick();
    let err = graph
        .node_attribute(NodeId(1), "social-class/imperial-rent")
        .expect_err("the periphery class must have no rent attribute at all");
    assert!(err.message.contains("never a default"), "{}", err.message);
}

#[test]
fn the_same_content_over_the_same_world_hashes_identically() {
    // Constitution III.7. This is the slice's definition of done: run the
    // whole path twice and the state hashes agree byte for byte.
    let (first, _, _) = run_one_tick();
    let (second, _, _) = run_one_tick();
    assert_eq!(
        first.state_hash().unwrap(),
        second.state_hash().unwrap(),
        "two identical runs must produce identical state"
    );
}

#[test]
fn the_tick_actually_changed_the_world() {
    // The dual, and the one that catches a tick that silently did nothing:
    // the post-tick hash must differ from the pre-tick hash. Without this,
    // a run_tick that returned Ok and executed no effect would pass every
    // other test in this file.
    let mut before = MemoryGraph::new();
    load_scenario(SCENARIO, &mut before).unwrap();
    let untouched = before.state_hash().unwrap();

    let (after, _, fired) = run_one_tick();
    assert_eq!(fired, 1);
    assert_ne!(
        untouched,
        after.state_hash().unwrap(),
        "a tick that fired an effect must move the state hash"
    );
}

#[test]
fn a_changed_scenario_changes_the_hash() {
    // The world is part of the fingerprint, not just the rules.
    let r = registries();
    let mut richer = MemoryGraph::new();
    load_scenario(
        r"
(scenario ft/two-classes
  (deffield social-class/wages int extensive)
  (deffield social-class/value-produced int extensive)
  (deffield social-class/imperial-rent int extensive)
  (node core NodeType/SOCIAL_CLASS
    (social-class/wages 121)
    (social-class/value-produced 80))
  (node periphery NodeType/SOCIAL_CLASS
    (social-class/wages 20)
    (social-class/value-produced 90)))
",
        &mut richer,
    )
    .unwrap();

    let ctx = LoadContext {
        vocabulary: &r.vocabulary,
        types: &r.types,
        ceilings: &r.ceilings,
        intrinsics: &r.intrinsics,
        systems: &r.systems,
        rule_file: "economics/fundamental-theorem.bsl",
    };
    let loaded = load_rule(FUNDAMENTAL_THEOREM, &ctx).unwrap();
    let mut sink = CollectingSink::default();
    run_tick(
        &loaded,
        &r.types,
        &EmptyIntrinsicHost,
        &mut richer,
        &mut sink,
        &r.intrinsics,
    )
    .unwrap();

    let (baseline, _, _) = run_one_tick();
    assert_ne!(
        baseline.state_hash().unwrap(),
        richer.state_hash().unwrap(),
        "one more unit of wages is a different world and must hash differently"
    );
}
