//! The transcribed conformance corpus (spec §5, §8.1): the 271-line
//! doctrine trap-DSL corpus (`tests/unit/domain/doctrine/test_mechanics.py`)
//! and the 628-line event-evaluator corpus
//! (`tests/unit/engine/test_event_evaluator.py`), ported with the
//! documented 4-point M8 delta at exactly the sites spec §5
//! "Grammar-superset honesty" names — each correction test cites the
//! Python line it replaces and the old vs. new behavior. The full
//! per-function disposition table is
//! `reports/p27-conformance-corpus-transcription.md`.
//!
//! The graph-query fixtures evaluate declared fields on heterogeneous
//! `MemoryGraph` nodes and pin the result and fuel (§6.1). Metric fixtures
//! use explicitly supplied bindings: they exercise expression evaluation
//! and collect-and-apply effects, not a runtime metric provider.
#![allow(clippy::doc_markdown)] // doc comments cite Python test names and file paths verbatim

use babylon_bsl::bindings::BindingVocabulary;
use babylon_bsl::evaluator::{evaluate, EvalEnv, Value};
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::EmptyIntrinsicHost;
use babylon_bsl::reader::read;
use babylon_bsl::rule_pipeline::{bind_environment, load_rule, LoadContext, LoadError, LoadedRule};
use babylon_bsl::structural_verbs::{CollectingSink, EffectExecutor};
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::{BslType, EnumRegistry, FieldDecl, FieldKind};
use babylon_graph::memory::MemoryGraph;
use babylon_graph::substrate::GraphSubstrate;
use babylon_kernel::currency::Currency;
use std::collections::{HashMap, HashSet};

// ---------------------------------------------------------------- context

fn field(ty: BslType, kind: FieldKind) -> FieldDecl {
    FieldDecl { ty, kind }
}

fn types() -> TypeEnv {
    TypeEnv {
        fields: HashMap::from([
            // Doctrine tag totals: accumulated counts, extensive.
            (
                "organization/mass-link".to_owned(),
                field(BslType::Int, FieldKind::Extensive),
            ),
            (
                "organization/class-analysis".to_owned(),
                field(BslType::Int, FieldKind::Extensive),
            ),
            (
                "organization/militancy".to_owned(),
                field(BslType::Int, FieldKind::Extensive),
            ),
            // Measured-practice variables: unit-interval shares, intensive.
            (
                "organization/solidarity-mass".to_owned(),
                field(BslType::Coefficient, FieldKind::Intensive),
            ),
            (
                "organization/co-optive-share".to_owned(),
                field(BslType::Coefficient, FieldKind::Intensive),
            ),
            (
                "organization/petty-bourgeois-drift".to_owned(),
                field(BslType::Coefficient, FieldKind::Intensive),
            ),
            // Event-evaluator estate.
            (
                "social-class/agitation".to_owned(),
                field(BslType::Intensity, FieldKind::Intensive),
            ),
            (
                "social-class/national-identity".to_owned(),
                field(BslType::Intensity, FieldKind::Intensive),
            ),
            (
                "social-class/class-consciousness".to_owned(),
                field(BslType::Intensity, FieldKind::Intensive),
            ),
            (
                "social-class/wealth".to_owned(),
                field(BslType::Currency, FieldKind::Extensive),
            ),
            (
                "social-class/population".to_owned(),
                field(BslType::Int, FieldKind::Extensive),
            ),
            (
                "solidarity/strength".to_owned(),
                field(BslType::Intensity, FieldKind::Intensive),
            ),
        ]),
        exemptions: &[],
    }
}

fn vocabulary() -> BindingVocabulary {
    let types = types();
    BindingVocabulary {
        fields: types.fields.keys().cloned().collect(),
        consts: HashSet::from([
            "doctrine/solidarity-liquidation-floor".to_owned(),
            "doctrine/co-optive-liquidation-threshold".to_owned(),
            "doctrine/petty-bourgeois-liquidation-threshold".to_owned(),
        ]),
        probability_consts: HashSet::new(),
        metrics: HashSet::from([
            // The six Python metrics (event_evaluator.py:301-310), as the
            // registered metric set.
            "solidarity-density".to_owned(),
            "exploitation-density".to_owned(),
            "average-agitation".to_owned(),
            "average-consciousness".to_owned(),
            "total-wealth".to_owned(),
            "gini-coefficient".to_owned(),
        ]),
    }
}

fn ceilings() -> CardinalityCeilings {
    CardinalityCeilings::new(
        HashMap::from([
            ("NodeType/SOCIAL_CLASS".to_owned(), 100),
            ("EdgeType/SOLIDARITY".to_owned(), 40),
        ]),
        HashMap::new(),
    )
}

struct Registries {
    vocabulary: BindingVocabulary,
    types: TypeEnv,
    ceilings: CardinalityCeilings,
    intrinsics: IntrinsicCosts,
    systems: HashSet<String>,
    /// No fixture in this corpus declares an enum-typed field — an empty
    /// registry is the honest "no `defenum`s in scope" input.
    enums: EnumRegistry,
}

fn registries() -> Registries {
    Registries {
        vocabulary: vocabulary(),
        types: types(),
        ceilings: ceilings(),
        intrinsics: IntrinsicCosts::default(),
        systems: HashSet::from(["doctrine".to_owned(), "event".to_owned()]),
        enums: EnumRegistry::default(),
    }
}

fn load(source: &str, rule_file: &str) -> Result<LoadedRule, LoadError> {
    let r = registries();
    let ctx = LoadContext {
        vocabulary: &r.vocabulary,
        types: &r.types,
        enums: &r.enums,
        const_values: Box::leak(Box::new(HashMap::new())),
        ceilings: &r.ceilings,
        intrinsics: &r.intrinsics,
        systems: &r.systems,
        vocabulary_registry: None,
        rule_file,
    };
    load_rule(source, &ctx)
}

/// The `<when>` clause of a loaded rule — shared by `eval_when` and its
/// graph-bearing twin `eval_when_over_graph` (PR 4, Task 14), plus the
/// slice-2-refusal vector for `event_edge_count.bsl`.
fn when_clause(rule: &LoadedRule) -> &babylon_bsl::reader::SExpr {
    let babylon_bsl::reader::SExpr::List(items) = &rule.rule else {
        unreachable!()
    };
    items
        .iter()
        .find_map(|child| match child {
            babylon_bsl::reader::SExpr::List(inner)
                if matches!(inner.first(), Some(babylon_bsl::reader::SExpr::Atom(babylon_bsl::reader::Atom::Symbol(h))) if h == "when") =>
            {
                inner.get(1)
            }
            _ => None,
        })
        .expect("fixture has a when clause")
}

/// Load a fixture and evaluate its `<when>` condition against supplied
/// binding values — the trap-DSL calling convention
/// (`evaluate_trap_condition(expr, env, coeffs)`) reconstructed from the
/// composed pipeline.
fn eval_when(rule: &LoadedRule, supplied: &HashMap<String, Value>) -> bool {
    let env_map = bind_environment(&rule.bindings, supplied).expect("environment must bind");
    let costs = IntrinsicCosts::default();
    let env = EvalEnv {
        bindings: env_map,
        intrinsic_costs: &costs,
        graph: None,
        types: None,
        enums: None,
        elements: Vec::new(),
        draw_context: None,
    };
    let mut fuel = 10_000;
    match evaluate(when_clause(rule), &env, &EmptyIntrinsicHost, &mut fuel)
        .expect("condition must evaluate")
    {
        Value::Bool(b) => b,
        other => panic!("a <cond> must be Bool, got {other:?}"),
    }
}

/// `eval_when`'s graph-bearing twin (PR 4, Task 14): the same calling
/// convention, but `env.graph = Some(graph)` — for fixtures whose
/// `<when>` materializes a `<query>` (§2.6) rather than reading only
/// rule-scope bindings. Takes the fuel meter BY REFERENCE, unlike
/// `eval_when`, so a caller can assert `:fuel-used` (§6.1) on the vector
/// that matters.
fn eval_when_over_graph(
    rule: &LoadedRule,
    supplied: &HashMap<String, Value>,
    graph: &dyn GraphSubstrate,
    fuel: &mut u64,
) -> bool {
    let env_map = bind_environment(&rule.bindings, supplied).expect("environment must bind");
    let costs = IntrinsicCosts::default();
    let declared_types = types();
    let enums = EnumRegistry::default();
    let env = EvalEnv {
        bindings: env_map,
        intrinsic_costs: &costs,
        graph: Some(graph),
        types: Some(&declared_types),
        enums: Some(&enums),
        elements: Vec::new(),
        draw_context: None,
    };
    match evaluate(when_clause(rule), &env, &EmptyIntrinsicHost, fuel)
        .expect("condition must evaluate")
    {
        Value::Bool(b) => b,
        other => panic!("a <cond> must be Bool, got {other:?}"),
    }
}

fn int(n: i64) -> Value {
    Value::Int(n)
}
fn real(r: f64) -> Value {
    Value::Real(r)
}

// ================================================================ doctrine
// tests/unit/domain/doctrine/test_mechanics.py (271 lines)

const ADVENTURISM: &str = include_str!("conformance/doctrine_adventurism.bsl");
const LIQUIDATIONISM: &str = include_str!("conformance/doctrine_liquidationism.bsl");
const ABSORBING: &str = include_str!("conformance/doctrine_liquidation_absorbing.bsl");

/// test_mechanics.py:45-64 (TestRealMvpConditions) — the two shipped MVP
/// trap conditions, behavior preserved exactly.
#[test]
fn real_mvp_conditions() {
    let adventurism = load(ADVENTURISM, "tests/conformance/doctrine_adventurism.bsl").unwrap();
    assert!(eval_when(&adventurism, &owned(vec![("mass-link", int(0))])));
    assert!(!eval_when(
        &adventurism,
        &owned(vec![("mass-link", int(3))])
    ));

    let liquidationism = load(
        LIQUIDATIONISM,
        "tests/conformance/doctrine_liquidationism.bsl",
    )
    .unwrap();
    assert!(eval_when(
        &liquidationism,
        &owned(vec![("class-analysis", int(0)), ("militancy", int(0))])
    ));
    assert!(!eval_when(
        &liquidationism,
        &owned(vec![("class-analysis", int(0)), ("militancy", int(5))])
    ));
}

/// test_mechanics.py:67-75 (TestMissingTagIsZero) — absent = no
/// accumulated strength. In BSL the honest-null site is DECLARED:
/// `:optional :default 0`, carried on the DEFAULT_ALLOWLIST.
#[test]
fn missing_tag_reads_the_declared_default() {
    let adventurism = load(ADVENTURISM, "tests/conformance/doctrine_adventurism.bsl").unwrap();
    // No value supplied at all: the declared default 0 applies -> fires.
    assert!(eval_when(&adventurism, &HashMap::new()));
    // The allowlist covers every :default this corpus declares — zero
    // sign-off findings.
    assert!(adventurism.default_findings.is_empty());
    let absorbing = load(
        ABSORBING,
        "tests/conformance/doctrine_liquidation_absorbing.bsl",
    )
    .unwrap();
    assert!(absorbing.default_findings.is_empty());
}

/// test_mechanics.py:85-134 (TestMeasuredPracticeVocabulary) — the U11
/// absorbing state over practice variables + coefficient thresholds.
#[test]
fn liquidation_absorbing_state() {
    let absorbing = load(
        ABSORBING,
        "tests/conformance/doctrine_liquidation_absorbing.bsl",
    )
    .unwrap();
    let coeffs = [
        ("solidarity-liquidation-floor", real(0.05)),
        ("co-optive-liquidation-threshold", real(0.6)),
        ("petty-bourgeois-liquidation-threshold", real(0.6)),
    ];
    // test_mechanics.py:114-117 — collapsed solidarity, high co-optation,
    // embourgeoised base: liquidated.
    let mut fires: Vec<(&str, Value)> = coeffs.to_vec();
    fires.extend([
        ("solidarity-mass", real(0.0)),
        ("co-optive-share", real(0.8)),
        ("petty-bourgeois-drift", real(0.7)),
    ]);
    assert!(eval_when(&absorbing, &owned(fires)));
    // test_mechanics.py:119-122 — a live SOLIDARITY mass base defeats the
    // absorbing state, whatever else.
    let mut dormant: Vec<(&str, Value)> = coeffs.to_vec();
    dormant.extend([
        ("solidarity-mass", real(0.5)),
        ("co-optive-share", real(0.8)),
        ("petty-bourgeois-drift", real(0.7)),
    ]);
    assert!(!eval_when(&absorbing, &owned(dormant)));
}

/// test_mechanics.py:124-138 — an unknown `@coeff` / unknown variable
/// fails LOUD. In BSL both are load-time resolution failures, not
/// evaluation-time surprises.
#[test]
fn unknown_coefficient_and_variable_fail_loud_at_load() {
    // Unknown coefficient: a :const outside the defines vocabulary.
    let unknown_coeff = ABSORBING.replace(
        ":const doctrine/solidarity-liquidation-floor",
        ":const doctrine/no-such-threshold",
    );
    let err = load(&unknown_coeff, "x.bsl").unwrap_err();
    assert_eq!(err.spec_code(), Some("E-LOAD-010"), "{err}");

    // Unknown variable: a free symbol no binding declares.
    let unknown_var = ADVENTURISM.replace("(<= mass-link 0)", "(<= not-a-variable 0)");
    let err = load(&unknown_var, "x.bsl").unwrap_err();
    assert_eq!(err.spec_code(), Some("E-LOAD-010"), "{err}");
}

/// test_mechanics.py:147-181 (TestFullGrammar) — all six comparisons,
/// AND/OR/NOT and grouping. Python's infix precedence ("AND binds tighter
/// than OR") is STRUCTURAL in BSL — s-expressions have no precedence to
/// get wrong, so the precedence test transcribes as explicit nesting.
#[test]
fn full_condition_grammar() {
    type Vector<'a> = (&'a str, &'a [(&'a str, Value)], bool);
    let vectors: &[Vector<'_>] = &[
        ("(>= ca 3)", &[("ca", Value::Int(3))], true),
        ("(> ca 3)", &[("ca", Value::Int(3))], false),
        ("(< ml 2)", &[("ml", Value::Int(1))], true),
        ("(= mi 4)", &[("mi", Value::Int(4))], true),
        ("(!= mi 4)", &[("mi", Value::Int(4))], false),
        (
            "(or (<= ml 0) (<= mi 0))",
            &[("ml", Value::Int(5)), ("mi", Value::Int(0))],
            true,
        ),
        (
            "(or (<= ml 0) (<= mi 0))",
            &[("ml", Value::Int(5)), ("mi", Value::Int(5))],
            false,
        ),
        ("(not (<= ml 0))", &[("ml", Value::Int(3))], true),
        ("(not (<= ml 0))", &[("ml", Value::Int(0))], false),
        (
            "(and (or (<= ca 0) (<= mi 0)) (<= ml 0))",
            &[
                ("ca", Value::Int(0)),
                ("mi", Value::Int(5)),
                ("ml", Value::Int(0)),
            ],
            true,
        ),
        (
            "(and (or (<= ca 0) (<= mi 0)) (<= ml 0))",
            &[
                ("ca", Value::Int(5)),
                ("mi", Value::Int(5)),
                ("ml", Value::Int(0)),
            ],
            false,
        ),
        // test_mechanics.py:177-181 — "A OR (B AND C)", nesting explicit.
        (
            "(or (<= ca 0) (and (<= ml 0) (<= mi 0)))",
            &[
                ("ca", Value::Int(0)),
                ("ml", Value::Int(0)),
                ("mi", Value::Int(5)),
            ],
            true,
        ),
    ];
    for (source, env_pairs, expected) in vectors {
        assert_eq!(eval_cond(source, env_pairs), *expected, "vector: {source}");
    }
}

/// test_mechanics.py:184-202 (TestMalformedRaises) — every malformed
/// condition fails LOUDLY, each through the §4.6 class its defect belongs
/// to; a trap that silently never fires is a correctness hole.
#[test]
fn malformed_conditions_fail_loud() {
    // "" — nothing to read.
    assert!(read("").is_err());
    // "MASS_LINK <=" — dangling operator: strictly binary arity.
    let err = eval_cond_err("(<= ml)", &[("ml", Value::Int(0))]);
    assert!(err.message.contains("E-PARSE-040"), "{err}");
    // "MASS_LINK 0" — missing comparison: the head is an undeclared call.
    let err = eval_cond_err("(ml 0)", &[("ml", Value::Int(0))]);
    assert!(err.message.contains("E-LOAD-021"), "{err}");
    // "UNKNOWN_TAG <= 0" — SCREAMING_SNAKE now lexes fine (#528 fix round:
    // a bare uppercase-with-underscore run is a legal <enum-member>-shaped
    // atom, §2.13's own EBNF for a defenum/defvocabulary member list), but
    // it is not a value in comparison/expression position — the refusal
    // moves from the reader (E-LEX-003) to evaluation.
    let err = eval_cond_err("(<= UNKNOWN_TAG 0)", &[]);
    assert!(
        err.message.contains("not a value in expression position"),
        "{err}"
    );
    // "MASS_LINK <= zero" — a non-literal RHS is a free variable: load error.
    let with_free = ADVENTURISM.replace("(<= mass-link 0)", "(<= mass-link zero)");
    assert_eq!(
        load(&with_free, "x.bsl").unwrap_err().spec_code(),
        Some("E-LOAD-010")
    );
    // "MASS_LINK <= 0 AND" / "(MASS_LINK <= 0" — unterminated forms.
    assert!(read("(and (<= ml 0)").is_err());
}

/// test_mechanics.py:249-258 (TestTheoreticalLabourAccrual) — surplus ×
/// allocation with the negative floor and the unit-interval clamp WRITTEN
/// AS CONTENT (an explicit `if` is honest math; only SILENT clamping is
/// banned, §3.3).
#[test]
fn theoretical_labor_accrual_vectors() {
    let accrual = "(if (< surplus 0) \
                     0 \
                     (* surplus (if (> alloc 1.0c) 1.0c (if (< alloc 0c) 0c alloc))))";
    let cases: &[(f64, f64, f64)] = &[
        (1000.0, 0.2, 200.0),
        (-500.0, 0.2, 0.0),
        (100.0, 1.5, 100.0),
        (100.0, -0.5, 0.0),
    ];
    for (surplus, alloc, expected) in cases {
        let value = eval_value(
            accrual,
            &[("surplus", real(*surplus)), ("alloc", real(*alloc))],
        );
        match value {
            Value::Real(r) => assert!(
                (r - expected).abs() < 1e-9,
                "accrue({surplus}, {alloc}) = {r}, expected {expected}"
            ),
            Value::Int(n) => {
                // The zero arms return the Int literal 0.
                #[allow(clippy::cast_precision_loss)]
                let as_real = n as f64;
                assert!((as_real - expected).abs() < 1e-9);
            }
            other => panic!("unexpected {other:?}"),
        }
    }
}

/// test_mechanics.py:261-271 (TestTagDecay) — multiplicative decay as an
/// expression: identical IEEE-754 arithmetic on both sides, so the
/// expected value is computed by the SAME formula, not an approx literal.
#[test]
fn tag_decay_vectors() {
    let decay = "(* total (- 1 rate))";
    for (total, rate) in [(100.0_f64, 0.0055_f64), (50.0, 0.0055), (7.0, 0.0)] {
        let value = eval_value(decay, &[("total", real(total)), ("rate", real(rate))]);
        assert_eq!(
            value,
            Value::Real(total * (1.0 - rate)),
            "decay({total}, {rate})"
        );
    }
}

// ============================================================== event corpus
// tests/unit/engine/test_event_evaluator.py (628 lines)

const BIFURCATION: &str = include_str!("conformance/event_bifurcation.bsl");
const NODE_CONDITION: &str = include_str!("conformance/event_node_condition.bsl");
const FORALL: &str = include_str!("conformance/event_forall.bsl");
const EDGE_COUNT: &str = include_str!("conformance/event_edge_count.bsl");
const WEALTH_AGGREGATES: &str = include_str!("conformance/event_wealth_aggregates.bsl");
const METRIC_CONDITIONS: &str = include_str!("conformance/event_metric_conditions.bsl");
const UNKNOWN_METRIC: &str = include_str!("conformance/unknown_metric.bsl");
const EMPTY_WHEN: &str = include_str!("conformance/empty_when.bsl");
const UNCONDITIONAL: &str = include_str!("conformance/unconditional.bsl");

/// test_event_evaluator.py:124-151 (TestCompare) — the six comparison
/// operators, exact vectors.
#[test]
fn compare_vectors() {
    let vectors: &[(&str, bool)] = &[
        ("(>= 5 5)", true),
        ("(>= 6 5)", true),
        ("(>= 4 5)", false),
        ("(<= 5 5)", true),
        ("(<= 4 5)", true),
        ("(<= 6 5)", false),
        ("(> 6 5)", true),
        ("(> 5 5)", false),
        ("(< 4 5)", true),
        ("(< 5 5)", false),
        ("(= 5 5)", true),
        ("(!= 5 5)", false),
    ];
    for (source, expected) in vectors {
        assert_eq!(eval_cond(source, &[]), *expected, "vector: {source}");
    }
    // 5.1 == 5.0 / != — the binary64 lane.
    assert!(!eval_cond("(= x 5)", &[("x", real(5.1))]));
    assert!(eval_cond("(!= x 5)", &[("x", real(5.1))]));
}

/// test_event_evaluator.py:154-179 (TestGetNestedValue) — dotted paths
/// become qname field paths; the missing-key-returns-None behavior does
/// NOT transcribe: absence is a load decision (`E-LOAD-010` or a declared
/// `:optional :default`), never a silently skipped None (§3.5).
#[test]
fn nested_paths_are_qnames_and_absence_is_declared() {
    // A declared field resolves...
    assert!(load(NODE_CONDITION, "x.bsl").is_ok());
    // ...an undeclared one is E-LOAD-010 at load, never a skipped None.
    let missing = NODE_CONDITION.replace("social-class/agitation", "social-class/missing");
    assert_eq!(
        load(&missing, "x.bsl").unwrap_err().spec_code(),
        Some("E-LOAD-010")
    );
    // A required binding with no supplied value is loud at bind time.
    let loaded = load(NODE_CONDITION, "x.bsl").unwrap();
    assert!(bind_environment(&loaded.bindings, &HashMap::new()).is_err());
}

/// test_event_evaluator.py:182-214 + 244-323 — aggregations become folds:
/// any -> exists, all -> forall, count/sum/max/min/weighted-mean load and
/// bound against declared ceilings. The load verdict pins here for all
/// four; three of the four ALSO execute for real below
/// (`node_condition_exists_executes_over_a_real_graph`,
/// `forall_executes_over_a_real_graph`,
/// `wealth_aggregates_execute_over_a_real_graph`) — `EDGE_COUNT`'s LOAD
/// verdict is pinned here too, but it ALSO executes for real now (T2,
/// issue #559) — see `edge_count_evaluates_for_real_on_an_empty_graph`/
/// `..._on_a_non_empty_graph` below.
#[test]
fn aggregation_fixtures_load_and_bound() {
    for (fixture, name) in [
        (NODE_CONDITION, "exists/any"),
        (FORALL, "forall/all"),
        (EDGE_COUNT, "count"),
        (WEALTH_AGGREGATES, "sum/max/min/weighted-mean"),
    ] {
        let loaded = load(fixture, "x.bsl").unwrap_or_else(|e| panic!("{name}: {e}"));
        assert!(loaded.static_bound > 0, "{name} has a real bound");
    }
}

/// Query predicates read each node, independently of the subject binding.
/// The equality and empty-query rows retain the declared boundary semantics.
#[test]
fn node_condition_exists_executes_over_a_real_graph() {
    let loaded = load(NODE_CONDITION, "x.bsl").unwrap();
    let cases: [(&str, &[f64], f64, bool, u64); 4] = [
        ("mixed, second node passes", &[0.25, 0.75], 0.1, true, 9),
        ("all below threshold", &[0.25, 0.5], 0.9, false, 9),
        ("exact threshold", &[0.6], 0.1, true, 6),
        ("empty", &[], 0.9, false, 3),
    ];
    for (label, values, subject_agitation, expected, expected_fuel) in cases {
        let graph = agitation_graph(values);
        let mut fuel = 10_000;
        assert_eq!(
            eval_when_over_graph(
                &loaded,
                &owned(vec![("agitation", real(subject_agitation))]),
                &graph,
                &mut fuel,
            ),
            expected,
            "{label}",
        );
        assert_eq!(10_000 - fuel, expected_fuel, "{label}: fuel used");
    }
}

/// One failing node defeats forall even when the subject binding passes;
/// forall over an empty population remains vacuously true (§4.4).
#[test]
fn forall_executes_over_a_real_graph() {
    let loaded = load(FORALL, "x.bsl").unwrap();
    let cases: [(&str, &[f64], f64, bool, u64); 3] = [
        ("all pass, including boundary", &[0.75, 0.5], 0.1, true, 9),
        ("mixed, second node fails", &[0.75, 0.25], 0.9, false, 9),
        ("empty", &[], 0.0, true, 3),
    ];
    for (label, values, subject_agitation, expected, expected_fuel) in cases {
        let graph = agitation_graph(values);
        let mut fuel = 10_000;
        assert_eq!(
            eval_when_over_graph(
                &loaded,
                &owned(vec![("agitation", real(subject_agitation))]),
                &graph,
                &mut fuel,
            ),
            expected,
            "{label}",
        );
        assert_eq!(10_000 - fuel, expected_fuel, "{label}: fuel used");
    }
}

fn agitation_graph(values: &[f64]) -> MemoryGraph {
    let mut graph = MemoryGraph::new();
    for value in values {
        let node = graph.add_node("SOCIAL_CLASS").unwrap();
        graph
            .update_node(node, "social-class/agitation", *value)
            .unwrap();
    }
    graph
}

fn currency(units: i64) -> Value {
    Value::Currency(Currency::from_micro_units(i128::from(units) * 1_000_000))
}

// Currency units, agitation, and population for one class node.
type ClassValues = (i64, f64, u32);

fn wealth_graph(rows: &[ClassValues]) -> MemoryGraph {
    let mut graph = MemoryGraph::new();
    for &(wealth, agitation, population) in rows {
        let node = graph.add_node("SOCIAL_CLASS").unwrap();
        graph
            .update_node_currency(
                node,
                "social-class/wealth",
                Currency::from_micro_units(i128::from(wealth) * 1_000_000),
            )
            .unwrap();
        graph
            .update_node(node, "social-class/agitation", agitation)
            .unwrap();
        graph
            .update_node(node, "social-class/population", f64::from(population))
            .unwrap();
    }
    graph
}

/// Deliberately different from the graph values: the folds must read their
/// elements, not repeat these subject bindings once per node.
fn wealth_subject_bindings() -> HashMap<String, Value> {
    owned(vec![
        ("wealth", currency(1)),
        ("agitation", real(0.9)),
        ("population", int(100)),
    ])
}

/// Currency stays in its declared lane; heterogeneous values distinguish
/// sum, extrema and the population-weighted mean from constant-body folds.
#[test]
fn wealth_aggregates_execute_over_a_real_graph() {
    let loaded = load(WEALTH_AGGREGATES, "x.bsl").unwrap();
    let graph = wealth_graph(&[(500, 0.75, 1), (50, 0.25, 3)]);
    let bindings = wealth_subject_bindings();
    for (operator, expected) in [
        ("sum", currency(550)),
        ("max", currency(500)),
        ("min", currency(50)),
    ] {
        let expression = format!(
            "(fold {operator} (nodes NodeType/SOCIAL_CLASS) (field-of it social-class/wealth))"
        );
        let mut fuel = 10_000;
        assert_eq!(
            eval_value_over_graph(&expression, &bindings, &graph, &mut fuel),
            expected,
            "{operator}"
        );
        assert_eq!(10_000 - fuel, 7, "{operator}: fuel used");
    }
    let mut mean_fuel = 10_000;
    assert_eq!(
        eval_value_over_graph(
            "(fold mean (nodes NodeType/SOCIAL_CLASS) (field-of it social-class/agitation) :weight (field-of it social-class/population))",
            &bindings,
            &graph,
            &mut mean_fuel,
        ),
        real(0.375),
    );
    assert_eq!(10_000 - mean_fuel, 11, "weighted mean: fuel used");

    let mut fuel = 10_000;
    assert!(eval_when_over_graph(&loaded, &bindings, &graph, &mut fuel));
    assert_eq!(10_000 - fuel, 37, "complete condition: fuel used");
}

/// Each negative case preserves every other condition. Unequal populations
/// also distinguish the intended weighted mean from an unweighted mean.
#[test]
fn wealth_aggregate_conditions_discriminate_each_threshold() {
    let loaded = load(WEALTH_AGGREGATES, "x.bsl").unwrap();
    let cases: [(&str, &[ClassValues]); 4] = [
        ("sum", &[(500, 0.75, 1), (49, 0.25, 3)]),
        ("maximum", &[(250, 0.75, 1), (250, 0.75, 1), (50, 0.25, 3)]),
        ("minimum", &[(500, 0.75, 1), (51, 0.25, 3)]),
        ("weighted mean", &[(500, 0.75, 1), (50, 0.125, 7)]),
    ];
    for (label, rows) in cases {
        let graph = wealth_graph(rows);
        let mut fuel = 10_000;
        assert!(
            !eval_when_over_graph(&loaded, &wealth_subject_bindings(), &graph, &mut fuel),
            "{label}"
        );
    }
    let graph = wealth_graph(&[(500, 0.75, 1), (50, 0.125, 7)]);
    let mut fuel = 10_000;
    assert_eq!(
        eval_value_over_graph(
            "(fold mean (nodes NodeType/SOCIAL_CLASS) (field-of it social-class/agitation) :weight (field-of it social-class/population))",
            &wealth_subject_bindings(),
            &graph,
            &mut fuel,
        ),
        real(0.203_125),
    );
    // The unweighted mean is 0.4375 and would incorrectly pass.
}

/// **T2 (issue #559, Task 3): event_edge_count.bsl now evaluates for real**, promoted from the
/// load-only pin `edge_count_stays_pinned_and_names_slice_2` used to be — `edges` is served as
/// of T2. An empty graph has zero SOLIDARITY edges: `(fold count (edges EdgeType/SOLIDARITY)
/// it)` is `0`, and `(>= 0 1)` is `false` — the exact vector T2 exists to unblock.
#[test]
fn edge_count_evaluates_for_real_on_an_empty_graph() {
    let loaded = load(EDGE_COUNT, "x.bsl").unwrap();
    let graph = MemoryGraph::new();
    let costs = IntrinsicCosts::default();
    let env_map = bind_environment(&loaded.bindings, &HashMap::new())
        .expect("EDGE_COUNT's bindings are empty — nothing to resolve");
    let env = EvalEnv {
        bindings: env_map,
        intrinsic_costs: &costs,
        graph: Some(&graph as &dyn GraphSubstrate),
        types: None,
        enums: None,
        elements: Vec::new(),
        draw_context: None,
    };
    let mut fuel = 10_000;
    let result = evaluate(when_clause(&loaded), &env, &EmptyIntrinsicHost, &mut fuel).unwrap();
    assert_eq!(
        result,
        Value::Bool(false),
        "an empty graph has zero SOLIDARITY edges"
    );
}

/// The non-empty companion: one SOLIDARITY edge is enough to cross the `>= 1` threshold.
#[test]
fn edge_count_evaluates_for_real_on_a_non_empty_graph() {
    let loaded = load(EDGE_COUNT, "x.bsl").unwrap();
    let mut graph = MemoryGraph::new();
    let a = graph.add_node("SOCIAL_CLASS").unwrap();
    let b = graph.add_node("SOCIAL_CLASS").unwrap();
    graph.add_edge("SOLIDARITY", a, b, 0.5).unwrap();
    let costs = IntrinsicCosts::default();
    let env_map = bind_environment(&loaded.bindings, &HashMap::new())
        .expect("EDGE_COUNT's bindings are empty — nothing to resolve");
    let env = EvalEnv {
        bindings: env_map,
        intrinsic_costs: &costs,
        graph: Some(&graph as &dyn GraphSubstrate),
        types: None,
        enums: None,
        elements: Vec::new(),
        draw_context: None,
    };
    let mut fuel = 10_000;
    let result = evaluate(when_clause(&loaded), &env, &EmptyIntrinsicHost, &mut fuel).unwrap();
    assert_eq!(
        result,
        Value::Bool(true),
        "one SOLIDARITY edge crosses the >= 1 threshold"
    );
}

/// §3.4 catches what Python's aggregate_and_compare silently permitted:
/// summing / unweighted-averaging an INTENSIVE field is the recorded
/// variance error. Python's `sum_strength`/`avg_strength`
/// (test_event_evaluator.py:307-323) and unweighted `avg` over agitation
/// are E-TYPE-041/042 here — a documented tightening, not a correction
/// row (the four M8 corrections are separate).
#[test]
fn intensive_aggregation_is_rejected_where_python_allowed_it() {
    let sum_strength = EDGE_COUNT.replace(
        "(fold count (edges EdgeType/SOLIDARITY) it)",
        "(fold sum (edges EdgeType/SOLIDARITY) solidarity/strength)",
    );
    assert_eq!(
        load(&sum_strength, "x.bsl").unwrap_err().spec_code(),
        Some("E-TYPE-041")
    );
    let avg_strength = EDGE_COUNT.replace(
        "(fold count (edges EdgeType/SOLIDARITY) it)",
        "(fold mean (edges EdgeType/SOLIDARITY) solidarity/strength)",
    );
    assert_eq!(
        load(&avg_strength, "x.bsl").unwrap_err().spec_code(),
        Some("E-TYPE-042")
    );
}

/// test_event_evaluator.py:326-369 (graph conditions + metrics) — the six
/// Python metrics are the registered :metric set; conditions over them
/// load, and their conjunction evaluates in the expression core.
#[test]
fn metric_conditions_load_and_evaluate() {
    let loaded = load(METRIC_CONDITIONS, "x.bsl").unwrap();
    // solidarity_graph analogue: density 2/6, wealth 550, agitation 0.4.
    let fires = [
        ("solidarity-density", real(2.0 / 6.0)),
        ("total-wealth", real(550.0)),
        ("average-agitation", real(0.4)),
    ];
    assert!(eval_when(&loaded, &owned(fires.to_vec())));
    // simple_graph analogue for density: no solidarity edges -> 0.0.
    let dormant = [
        ("solidarity-density", real(0.0)),
        ("total-wealth", real(550.0)),
        ("average-agitation", real(0.4)),
    ];
    assert!(!eval_when(&loaded, &owned(dormant.to_vec())));
}

/// test_event_evaluator.py:372-417 (PreconditionSet logic) — "all" is
/// `and`, "any" is `or`; both short-circuit per §4.1.
#[test]
fn precondition_logic_vectors() {
    let all = "(and (>= agitation 0.6p) (>= wealth 1000))";
    assert!(!eval_cond(
        all,
        &[("agitation", real(0.7)), ("wealth", real(550.0))]
    ));
    let any = "(or (>= agitation 0.6p) (>= wealth 1000))";
    assert!(eval_cond(
        any,
        &[("agitation", real(0.7)), ("wealth", real(550.0))]
    ));
}

/// Supplied graph-metric bindings exercise the real condition evaluator and
/// collect-and-apply path. This is not full tick execution: the current tick
/// driver deliberately refuses metric bindings without a runtime provider.
#[test]
fn bifurcation_routes_by_solidarity_density() {
    let loaded = load(BIFURCATION, "x.bsl").unwrap();
    for (agitation, density, expected_national, expected_class) in [
        (0.49, 0.05, 0.2_f64, 0.4_f64),
        (0.49, 0.1, 0.2, 0.4),
        (0.5, 0.05, 0.2 + 0.15, 0.4),
        (0.5, 0.1, 0.2, 0.4 + 0.15),
        (0.5, 0.2, 0.2, 0.4 + 0.15),
    ] {
        let mut graph = MemoryGraph::new();
        let self_id = graph.add_node("SOCIAL_CLASS").unwrap();
        graph
            .update_node(self_id, "social-class/national-identity", 0.2)
            .unwrap();
        graph
            .update_node(self_id, "social-class/class-consciousness", 0.4)
            .unwrap();

        let supplied = owned(vec![
            ("agitation", real(agitation)),
            ("solidarity-density", real(density)),
            ("self", Value::NodeRef(self_id)),
        ]);
        let mut env_map = bind_environment(&loaded.bindings, &supplied).unwrap();
        env_map.insert("self".to_owned(), Value::NodeRef(self_id));
        let costs = IntrinsicCosts::default();
        let registries = registries();
        let env = EvalEnv {
            bindings: env_map,
            intrinsic_costs: &costs,
            graph: Some(&graph),
            types: Some(&registries.types),
            enums: Some(&registries.enums),
            elements: Vec::new(),
            draw_context: None,
        };
        let babylon_bsl::reader::SExpr::List(items) = &loaded.rule else {
            unreachable!()
        };
        let effects = items
            .iter()
            .find_map(|child| match child {
                babylon_bsl::reader::SExpr::List(inner)
                    if matches!(inner.first(), Some(babylon_bsl::reader::SExpr::Atom(babylon_bsl::reader::Atom::Symbol(h))) if h == "effects") =>
                {
                    Some(&inner[1..])
                }
                _ => None,
            })
            .unwrap();
        let mut executor = EffectExecutor::new(&registries.types, &registries.enums);
        let mut sink = CollectingSink::default();
        let mut fuel = loaded.declared_fuel;
        let pending = match evaluate(when_clause(&loaded), &env, &EmptyIntrinsicHost, &mut fuel)
            .expect("the bifurcation condition must evaluate")
        {
            Value::Bool(true) => executor
                .collect_effects(effects, &env, &EmptyIntrinsicHost, &mut sink, &mut fuel)
                .unwrap(),
            Value::Bool(false) => Vec::new(),
            other => panic!("a condition must be Bool, got {other:?}"),
        };
        for write in &pending {
            executor.apply_pending_write(write, &mut graph).unwrap();
        }
        for (field, expected) in [
            ("social-class/national-identity", expected_national),
            ("social-class/class-consciousness", expected_class),
        ] {
            assert_eq!(
                graph.node_attribute(self_id, field).unwrap().to_bits(),
                expected.to_bits(),
                "agitation {agitation}, density {density}: {field}",
            );
        }
    }
}

// ------------------------------------------------- the four M8 corrections

/// CORRECTION 1 of 4 — event_evaluator.py:313: `calculator() if
/// calculator else 0.0`. Old: an unknown graph metric silently reads 0.0.
/// New: an unregistered :metric is E-LOAD-011 at content load (§2.5) —
/// the rule never loads, nothing reads a phantom zero.
#[test]
fn correction_1_unknown_metric_is_e_load_011_not_zero() {
    let err = load(UNKNOWN_METRIC, "x.bsl").unwrap_err();
    assert_eq!(err.spec_code(), Some("E-LOAD-011"), "{err}");
}

/// CORRECTION 2 of 4 — event_evaluator.py:439: the aggregation dispatch
/// falls through to `return False`. Old: an unknown aggregation silently
/// never fires. New: an off-set fold operator is `E-PARSE-015` at parse.
///
/// **Code sharpened by R9 chapter C8 (D75).** This vector previously
/// asserted only the message text, because §6.3's disposition table named
/// the behaviour ("unknown aggregation → `E-PARSE-015` at parse") while no
/// numbered code existed to assert. D75 supplies it, and the grammar pass
/// now rejects the off-set head before the §3.4 checker sees it — an
/// earlier, better-classified rejection of the same content.
#[test]
fn correction_2_unknown_aggregation_is_e_parse_015_not_false() {
    let median = EDGE_COUNT.replace(
        "(fold count (edges EdgeType/SOLIDARITY) it)",
        "(fold median (edges EdgeType/SOLIDARITY) solidarity/strength)",
    );
    let err = load(&median, "x.bsl").unwrap_err();
    assert_eq!(err.spec_code(), Some("E-PARSE-015"), "{err}");
}

/// CORRECTION 3 of 4 — event_evaluator.py:405: the comparison dispatch
/// falls through to `return False`. Old: an unknown operator silently
/// never fires. New: a token outside the closed operator set is not even
/// an atom — E-LEX-003 at read time.
#[test]
fn correction_3_unknown_comparison_operator_is_a_lex_error_not_false() {
    let err = read("(~= agitation 0.5p)").unwrap_err();
    assert!(matches!(
        err.kind,
        babylon_bsl::reader::ReadErrorKind::Lex(babylon_bsl::reader::LexCode::UnclassifiableToken)
    ));
}

/// CORRECTION 4 of 4 — event_evaluator.py:103: `if not results: return
/// True`. Old: an empty precondition set silently always passes. New:
/// `(when)` is a loud load rejection (E-PARSE-020); "always" is written by
/// omitting the clause — explicit intent, never an accident.
#[test]
fn correction_4_empty_when_is_rejected_and_omission_is_the_legal_always() {
    let err = load(EMPTY_WHEN, "x.bsl").unwrap_err();
    assert!(err.to_string().contains("E-PARSE-020"), "{err}");
    let unconditional = load(UNCONDITIONAL, "x.bsl").unwrap();
    assert_eq!(
        unconditional.static_bound, 3,
        "an omitted <when> contributes 0; the emit costs 3"
    );
}

// ---------------------------------------------------------------- helpers

fn owned(pairs: Vec<(&str, Value)>) -> HashMap<String, Value> {
    pairs
        .into_iter()
        .map(|(name, value)| (name.to_owned(), value))
        .collect()
}

fn eval_value(source: &str, env_pairs: &[(&str, Value)]) -> Value {
    let costs = IntrinsicCosts::default();
    let env = EvalEnv {
        bindings: owned(env_pairs.to_vec()),
        intrinsic_costs: &costs,
        graph: None,
        types: None,
        enums: None,
        elements: Vec::new(),
        draw_context: None,
    };
    let (expr, _) = read(source).expect("vector source must parse");
    let mut fuel = 10_000;
    evaluate(&expr, &env, &EmptyIntrinsicHost, &mut fuel).expect("vector must evaluate")
}

/// `eval_value`'s graph-bearing twin (PR 4, Task 14): `env.graph =
/// Some(graph)`, and the fuel meter is BY REFERENCE so a caller can
/// assert `:fuel-used` (§6.1).
fn eval_value_over_graph(
    source: &str,
    bindings: &HashMap<String, Value>,
    graph: &dyn GraphSubstrate,
    fuel: &mut u64,
) -> Value {
    let costs = IntrinsicCosts::default();
    let declared_types = types();
    let enums = EnumRegistry::default();
    let env = EvalEnv {
        bindings: bindings.clone(),
        intrinsic_costs: &costs,
        graph: Some(graph),
        types: Some(&declared_types),
        enums: Some(&enums),
        elements: Vec::new(),
        draw_context: None,
    };
    let (expr, _) = read(source).expect("vector source must parse");
    evaluate(&expr, &env, &EmptyIntrinsicHost, fuel).expect("vector must evaluate")
}

fn eval_cond(source: &str, env_pairs: &[(&str, Value)]) -> bool {
    match eval_value(source, env_pairs) {
        Value::Bool(b) => b,
        other => panic!("a <cond> must be Bool, got {other:?}"),
    }
}

fn eval_cond_err(source: &str, env_pairs: &[(&str, Value)]) -> babylon_bsl::evaluator::EvalError {
    let costs = IntrinsicCosts::default();
    let env = EvalEnv {
        bindings: owned(env_pairs.to_vec()),
        intrinsic_costs: &costs,
        graph: None,
        types: None,
        enums: None,
        elements: Vec::new(),
        draw_context: None,
    };
    let (expr, _) = read(source).expect("vector source must parse");
    let mut fuel = 10_000;
    evaluate(&expr, &env, &EmptyIntrinsicHost, &mut fuel).expect_err("vector must fail")
}
