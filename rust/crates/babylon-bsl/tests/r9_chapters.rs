//! The R9 gap-fill chapters' conformance families (`bsl-language.rst` §6.2
//! families 10–22). One module per chapter, in the §7 dependency order the
//! chapters were planned in (C1 → C13).
//!
//! **Scope honesty, recorded once here rather than per family.** §6.2's
//! families mix load-time and evaluation-time obligations. The crate's
//! evaluator is the §4 *expression core*: queries, folds, selections,
//! accessors and effect-position iteration have no runtime yet (the
//! `conformance_corpus.rs` header records the same boundary for the
//! pre-R9 estate). Every vector below therefore pins the obligation at the
//! time the language reference assigns it **and that this crate can
//! observe**: the `E-LEX`/`E-PARSE`/`E-TYPE`/`E-LOAD` classes execute for
//! real, and each `E-EVAL` row is pinned as its code's identity and
//! discipline rather than as a raised value. Rows that need the query
//! evaluator are named in the per-family notes, never silently skipped.

use babylon_bsl::bound_checker::{expr_cost, rule_bound, BoundError};
use babylon_bsl::declarations::{check_intrinsic_name, FieldRegistry};
use babylon_bsl::evaluator::EvalCode;
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::reader::{read, SExpr};
use babylon_bsl::scope::check_foreign_field_scoping;
use babylon_bsl::typecheck::{typecheck_aggregation, TypeCode, TypeEnv};
use babylon_bsl::vocabulary::{ClosedVocabulary, EnumKind};
use std::collections::HashMap;

// ------------------------------------------------------------- fixtures

fn vocabulary() -> ClosedVocabulary {
    ClosedVocabulary::new([
        (
            EnumKind::NodeType,
            vec![
                "SOCIAL_CLASS".to_owned(),
                "ORGANIZATION".to_owned(),
                "TERRITORY".to_owned(),
                "POLITY".to_owned(),
            ],
        ),
        (
            EnumKind::EdgeType,
            vec![
                "SOLIDARITY".to_owned(),
                "EXPLOITATION".to_owned(),
                "IN_SCALE".to_owned(),
            ],
        ),
        (
            EnumKind::HyperedgeType,
            vec!["ECONOMIC_SECTOR".to_owned(), "COMMUNITY".to_owned()],
        ),
        (EnumKind::EventType, vec!["RUPTURE".to_owned()]),
    ])
    .expect("the R9 fixture vocabulary is disjoint")
}

fn ceilings() -> CardinalityCeilings {
    CardinalityCeilings::new(
        HashMap::from([
            ("NodeType/SOCIAL_CLASS".to_owned(), 100),
            ("NodeType/ORGANIZATION".to_owned(), 40),
            ("NodeType/TERRITORY".to_owned(), 3000),
            ("NodeType/POLITY".to_owned(), 1),
            ("EdgeType/SOLIDARITY".to_owned(), 40),
            ("EdgeType/EXPLOITATION".to_owned(), 60),
            ("EdgeType/IN_SCALE".to_owned(), 5000),
            ("HyperedgeType/ECONOMIC_SECTOR".to_owned(), 500),
            ("HyperedgeType/COMMUNITY".to_owned(), 200),
        ]),
        HashMap::from([
            ("HyperedgeType/ECONOMIC_SECTOR".to_owned(), 32),
            ("HyperedgeType/COMMUNITY".to_owned(), 64),
        ]),
    )
}

fn e(source: &str) -> SExpr {
    read(source).expect("test source must parse").0
}

fn cost(source: &str) -> Result<u64, BoundError> {
    expr_cost(&e(source), &ceilings(), &IntrinsicCosts::default())
}

fn bound(source: &str) -> Result<u64, BoundError> {
    rule_bound(&e(source), &ceilings(), &IntrinsicCosts::default())
}

/// The §3.4 environment: the implicit `<edge-type>/strength` rows (D32) plus
/// the authored fields these families read.
fn type_env() -> TypeEnv {
    let v = vocabulary();
    let mut registry = FieldRegistry::with_implicit_edge_strength(&v);
    for source in [
        "(deffield social-class/wealth :type currency :kind extensive)",
        "(deffield social-class/agitation :type intensity :kind intensive)",
        "(deffield social-class/population :type int :kind extensive)",
        "(deffield exploitation/tension :type intensity :kind intensive)",
        "(deffield exploitation/value-flow :type currency :kind extensive)",
        "(deffield economic-sector/output :type currency :kind extensive)",
        "(deffield organization/claim-strength :type coefficient :kind intensive)",
        "(deffield territory/wage-bill :type currency :kind extensive)",
        "(deffield polity/imperial-rent-pool :type currency :kind extensive)",
    ] {
        registry.declare(&e(source), &v).expect(source);
    }
    TypeEnv {
        fields: registry.type_env_fields(),
        exemptions: &[],
    }
}

/// The §3.4 verdict for one aggregation shape: `None` accepts, `Some(code)`
/// is the rejection's code.
fn aggregation_code(source: &str) -> Option<TypeCode> {
    match typecheck_aggregation(&e(source), &type_env()) {
        Ok(_) => None,
        Err(err) => Some(err.code.expect("a §3.4 rejection carries its code")),
    }
}

const PREAMBLE: &str = ":material-basis \"the wage relation\" :fuel 65536";

fn rule(body: &str) -> String {
    format!("(rule demo/r9 {PREAMBLE} {body})")
}

// ====================================================== family 10 — C1
// Edge and hyperedge attributes (§2.4, §2.5, §2.9, §2.10).
//
// Runtime rows deferred to the query evaluator and named here: the
// `field-of` reads over a live `EdgeRef` / `HyperedgeRef` / `NodeRef`, and
// the `E-EVAL-033` wrong-referent raise. Their codes' identity is pinned
// below; their raise sites arrive with the Phase-2 evaluator.
mod c1_edge_and_hyperedge_attributes {
    use super::{
        aggregation_code, bound, check_foreign_field_scoping, check_intrinsic_name, cost, e,
        vocabulary, ClosedVocabulary, EnumKind, EvalCode, FieldRegistry, TypeCode,
    };
    use babylon_bsl::bindings::parse_bindings;

    /// §2.4's coverage row, both halves: `sum_strength` folds over the
    /// implicit `<edge-type>/strength` (extensive, so `sum` is legal), and
    /// `avg_strength` is its unweighted `mean` — also legal, for the same
    /// reason. An intensive `strength` would have made both `E-TYPE-041`.
    #[test]
    fn the_edge_condition_coverage_row_is_writable_as_sum_and_as_mean() {
        assert_eq!(aggregation_code("(sum solidarity/strength)"), None);
        assert_eq!(aggregation_code("(mean solidarity/strength)"), None);
    }

    /// A genuinely intensive edge attribute carries §3.4's obligation
    /// unchanged: `sum` is `E-TYPE-041` and the unweighted `mean` is
    /// `E-TYPE-042`, while the weighted `mean` accepts.
    #[test]
    fn an_intensive_edge_field_carries_the_weight_obligation() {
        assert_eq!(
            aggregation_code("(sum exploitation/tension)"),
            Some(TypeCode::SumOfIntensive)
        );
        assert_eq!(
            aggregation_code("(mean exploitation/tension)"),
            Some(TypeCode::UnweightedMeanOfIntensive)
        );
        assert!(babylon_bsl::typecheck::typecheck_aggregation(
            &e("(mean exploitation/tension :weight exploitation/value-flow)"),
            &super::type_env()
        )
        .is_ok());
    }

    /// §3.7 (D38): the accessor is a keyed lookup at `1 + operands`, never
    /// multiplied by a ceiling. The §2.10 worked shape's whole bound:
    /// `2 + query(1) + 60 × (field-of(2) + weight field-of(2)) = 243`.
    #[test]
    fn field_of_costs_one_plus_its_operand_and_never_a_ceiling() {
        assert_eq!(cost("(field-of it solidarity/strength)"), Ok(2));
        assert_eq!(cost("(field-of self social-class/wealth)"), Ok(2));
        assert_eq!(
            bound(&super::rule(
                "(bindings) (effects (emit EventType/RUPTURE \
                 (t (fold mean (edges EdgeType/EXPLOITATION) \
                     (field-of it exploitation/tension) \
                     :weight (field-of it exploitation/value-flow)))))"
            )),
            Ok(3 + 243)
        );
    }

    /// D32: re-declaring the implicit `<edge-type>/strength` is a duplicate
    /// field declaration, so its type and kind have exactly one home.
    #[test]
    fn redeclaring_the_implicit_strength_field_is_e_load_001() {
        let v = vocabulary();
        let mut registry = FieldRegistry::with_implicit_edge_strength(&v);
        let err = registry
            .declare(
                &e("(deffield exploitation/strength :type coefficient :kind extensive)"),
                &v,
            )
            .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-001"));
    }

    /// D31: a `deffield` whose first segment names no registered
    /// `NodeType`, `EdgeType` or `HyperedgeType` member.
    #[test]
    fn an_unregistered_field_owner_is_e_load_023() {
        let v = vocabulary();
        let mut registry = FieldRegistry::default();
        let err = registry
            .declare(
                &e("(deffield imperium/rent :type currency :kind extensive)"),
                &v,
            )
            .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-023"));
    }

    /// D31: the three renderings must be pairwise disjoint, checked once
    /// per content set over the whole vocabulary.
    #[test]
    fn a_node_edge_rendering_collision_is_e_load_032() {
        let err = ClosedVocabulary::new([
            (EnumKind::NodeType, vec!["TENANCY".to_owned()]),
            (EnumKind::EdgeType, vec!["TENANCY".to_owned()]),
        ])
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-LOAD-032");
    }

    /// D30: the same foreign-type reference under two enclosing bodies of
    /// that type is ambiguous — repaired by naming an element with `:as`.
    #[test]
    fn an_ambiguous_foreign_field_reference_is_e_type_013() {
        let source = super::rule(
            "(bindings (binding claim :field organization/claim-strength)) \
             (when (< (fold sum (nodes NodeType/ORGANIZATION) \
                        (fold max (nodes NodeType/ORGANIZATION) claim)) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        );
        let form = e(&source);
        let decls = parse_bindings(&form).unwrap();
        let err = check_foreign_field_scoping(&form, &decls, Some("social-class"), &vocabulary())
            .unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-013");
    }

    /// D33: every §5.2 form-head symbol is reserved against the intrinsic
    /// namespace, so `(field-of it x/y)` can never be a call.
    #[test]
    fn an_intrinsic_named_for_a_form_head_is_e_load_024() {
        for name in ["field-of", "fold", "the", "edge-between", "select-max"] {
            assert_eq!(
                check_intrinsic_name(name).unwrap_err().spec_code(),
                Some("E-LOAD-024"),
                "{name}"
            );
        }
    }

    /// D34: the accessor's absence discipline has exactly one code, and it
    /// is the same one `E-TYPE-014` degrades to on the update verbs, whose
    /// element is a reference §3.1 gives no static type.
    #[test]
    fn the_accessor_absence_discipline_is_e_eval_033() {
        assert_eq!(
            EvalCode::AccessorTypeOrValueMismatch.spec_code(),
            "E-EVAL-033"
        );
    }
}

// ====================================================== family 11 — C2
// Edge mutation (§2.8's `update-edge`, §2.10's `edge-between`, §3.9's
// hydration key).
//
// **Declared substrate gap, recorded rather than faked.** `update-edge`
// writes a declared field of an edge, and `GraphSubstrate` stores an edge as
// one `f64` strength keyed by `(type, from, to)` — it has no field storage.
// Widening it widens the canonical `state_hash` field set, which is
// hash-relevant and outside this chapter's licence (Constitution III.7). So
// the four `<update-op>` executions, the `E-EVAL-020` range boundary and the
// `E-EVAL-030` I.15 transition are **not** pinned as executions here; the
// verb's grammar, cost, static checks and codes are.
mod c2_edge_mutation {
    use super::{bound, cost, e, vocabulary};
    use babylon_bsl::evaluator::EvalCode;
    use babylon_bsl::grammar::{check_enum_ref_kinds, check_field_init_owners};
    use babylon_bsl::scenario::load_scenario;
    use babylon_graph::memory::MemoryGraph;

    /// D35: `update-edge` is a structural verb and costs like one —
    /// `3 + Σ operands`, with the update-op's own `1 + operand` inside it.
    #[test]
    fn update_edge_is_a_structural_verb_at_the_structural_verb_cost() {
        // 3 + element(1) + qname(0) + scale(1 + 0) = 5, the same shape as
        // §5.6's `update-node`.
        assert_eq!(
            cost("(update-edge it solidarity/strength (scale 0.95c))"),
            Ok(5)
        );
    }

    /// D36: endpoint-holding rules reach the edge through `edge-between`,
    /// which is a keyed lookup — `1 + Σ operands`, never a ceiling factor.
    #[test]
    fn edge_between_costs_one_plus_its_two_endpoint_operands() {
        assert_eq!(cost("(edge-between EdgeType/SOLIDARITY self other)"), Ok(3));
        // The §2.10 worked shape, whole: 3 + edge-between(3) + qname(0) +
        // scale(1 + 0) = 7.
        assert_eq!(
            cost(
                "(update-edge (edge-between EdgeType/SOLIDARITY self other) \
                 solidarity/strength (scale 0.95c))"
            ),
            Ok(7)
        );
    }

    /// §3.8 item 8's writable idiom, priced: a fold over `neighbors` that
    /// resolves each edge by key. `edge-between` is `1 + 0 + 1 + 1 = 3`,
    /// `field-of` is `1 + 3 = 4`, the fold is
    /// `2 + query(1 + self) + ceiling × 4`, and the `emit` around it adds
    /// its structural-verb base of 3. §3.7 charges the extra keyed lookup
    /// per neighbour and nothing more — the accessors never multiply.
    /// The ceiling is 40 (`EdgeType/SOLIDARITY`), which C8's D52 revision
    /// leaves unchanged here: `min(40, 100)` is still 40.
    #[test]
    fn the_self_anchored_endpoint_idiom_is_bounded() {
        assert_eq!(
            bound(&super::rule(
                "(bindings) (effects (emit EventType/RUPTURE \
                 (s (fold sum (neighbors self EdgeType/SOLIDARITY :in \
                                NodeType/SOCIAL_CLASS) \
                      (field-of (edge-between EdgeType/SOLIDARITY it self) \
                                solidarity/strength)))))"
            )),
            Ok(3 + 164)
        );
    }

    /// D37: the `:strength` operand is the implicit field's only writer at
    /// mint time — two writers in one form is an authoring bug.
    #[test]
    fn an_add_edge_field_init_naming_strength_is_e_parse_041() {
        let err = check_field_init_owners(
            &e("(add-edge EdgeType/SOLIDARITY a b :strength 0.5c (solidarity/strength 0.9c))"),
            &vocabulary(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-PARSE-041");
    }

    /// D37's other half, static on the minting verbs.
    #[test]
    fn an_add_edge_field_init_owning_off_another_type_is_e_type_014() {
        let err = check_field_init_owners(
            &e("(add-edge EdgeType/SOLIDARITY a b :strength 0.5c (social-class/wealth 5$))"),
            &vocabulary(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-014");
    }

    /// D74 at `edge-between`'s operand: a `NodeType` there is a kind error.
    #[test]
    fn an_edge_between_naming_a_node_type_is_e_type_011() {
        let err = check_enum_ref_kinds(&e("(edge-between NodeType/SOCIAL_CLASS a b)")).unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-011");
    }

    /// D73: hydration seeding one `(source, target, type)` triple twice is
    /// `E-LOAD-044` — the clause that makes the triple a **key** rather than
    /// a sort field, and the one §2.6's total order was resting on.
    #[test]
    fn a_hydration_seeding_one_edge_key_twice_is_e_load_044() {
        let source = "(scenario demo/dup
  (node core NodeType/SOCIAL_CLASS)
  (node periphery NodeType/SOCIAL_CLASS)
  (edge EdgeType/SOLIDARITY core periphery 1)
  (edge EdgeType/SOLIDARITY core periphery 1))";
        let mut graph = MemoryGraph::default();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-044"));
    }

    /// The same pair under a DIFFERENT edge type is a different key and
    /// hydrates — the triple is the key, not the pair.
    #[test]
    fn the_same_pair_under_another_edge_type_is_a_different_key() {
        let source = "(scenario demo/two-types
  (node core NodeType/SOCIAL_CLASS)
  (node periphery NodeType/SOCIAL_CLASS)
  (edge EdgeType/SOLIDARITY core periphery 1)
  (edge EdgeType/EXPLOITATION core periphery 1))";
        let mut graph = MemoryGraph::default();
        assert_eq!(load_scenario(source, &mut graph).unwrap().edge_count, 2);
    }

    /// D36: `edge-between` never yields an absent reference and never
    /// degrades to a no-op write — absence has its own code.
    #[test]
    fn an_unresolvable_edge_between_is_e_eval_034() {
        assert_eq!(EvalCode::NoSuchEdge.spec_code(), "E-EVAL-034");
    }
}

// ====================================================== family 12 — C3
// Graph-scope carriers (§2.10's `the`, §3.6's carrier ruling).
//
// Runtime rows deferred: `the`'s resolution against a hydrated carrier, its
// `E-EVAL-035` against an unhydrated one, and the accumulation vector whose
// value is sensitive to §4.2's subject order — all need the query evaluator
// and D44's subject enumeration. Their codes and static gates are pinned.
mod c3_graph_scope_carriers {
    use super::{cost, e};
    use babylon_bsl::evaluator::EvalCode;
    use babylon_bsl::grammar::check_enum_ref_kinds;
    use babylon_bsl::manifest::{check_rule_against_manifest, Manifest};

    const MANIFEST: &str = "(manifest r9
       (ceiling NodeType/SOCIAL_CLASS :ceiling 100)
       (ceiling NodeType/POLITY :ceiling 1)
       (ceiling NodeType/TERRITORY :ceiling 3000 :invariant)
       (ceiling EdgeType/SOLIDARITY :ceiling 40)
       (ceiling EdgeType/EXPLOITATION :ceiling 60)
       (ceiling EdgeType/IN_SCALE :ceiling 5000 :invariant)
       (ceiling HyperedgeType/COMMUNITY :ceiling 200 :max-members 64)
       (ceiling HyperedgeType/ECONOMIC_SECTOR :ceiling 500 :max-members 32))";

    fn manifest() -> Manifest {
        Manifest::parse(&e(MANIFEST)).expect("the R9 manifest is well formed")
    }

    fn carrier_rule(body: &str) -> babylon_bsl::reader::SExpr {
        e(&super::rule(&format!("(bindings) (effects {body})")))
    }

    /// D40 + §3.7's `cost(the) = 1`: reaching a singleton carrier costs a
    /// keyed lookup, NOT the degenerate fold's `2 + query + ceiling × body`
    /// the language previously forced.
    #[test]
    fn the_costs_one_where_the_degenerate_fold_cost_a_ceiling_factor() {
        assert_eq!(cost("(the NodeType/POLITY)"), Ok(1));
        // (update-node (the …) <qname> (sub drawn)) = 3 + 1 + 0 + (1 + 1) = 6,
        // against 2 + 1 + 1 × 2 = 5 for the fold plus the verb's own 3 + …
        assert_eq!(
            cost("(update-node (the NodeType/POLITY) polity/imperial-rent-pool (sub drawn))"),
            Ok(6)
        );
    }

    /// D40: legality is conditioned on the manifest's `:ceiling` being
    /// exactly 1 — the same declared number §3.7 already uses for the fuel
    /// bound, so the ruling adds no second registry.
    #[test]
    fn the_against_a_ceiling_one_carrier_loads_and_otherwise_is_e_load_043() {
        assert_eq!(
            check_rule_against_manifest(
                &carrier_rule(
                    "(update-node (the NodeType/POLITY) polity/imperial-rent-pool (sub 5$))"
                ),
                &manifest()
            ),
            Ok(())
        );
        let err = check_rule_against_manifest(
            &carrier_rule("(update-node (the NodeType/SOCIAL_CLASS) social-class/wealth (add 5$))"),
            &manifest(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-043"));
    }

    /// A carrier field is read and written as ORDINARY node state — no new
    /// grammar and no second storage class (D39).
    #[test]
    fn a_carrier_field_reads_with_field_of_and_writes_with_update_node() {
        assert_eq!(
            check_rule_against_manifest(
                &carrier_rule(
                    "(guard (< (field-of (the NodeType/POLITY) polity/imperial-rent-pool) 5$) \
                     (update-node (the NodeType/POLITY) polity/imperial-rent-pool (set 0$)))"
                ),
                &manifest()
            ),
            Ok(())
        );
    }

    /// D74 at `the`'s operand.
    #[test]
    fn the_against_an_edge_type_is_e_type_011() {
        let err = check_enum_ref_kinds(&e("(the EdgeType/SOLIDARITY)")).unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-011");
    }

    /// D76: a carrier type the manifest has no row for is `E-LOAD-045` —
    /// `E-LOAD-043`'s "other than 1" test cannot fire on a missing row, so
    /// the omission must be its own rejection.
    #[test]
    fn a_manifest_with_no_row_for_the_carrier_type_is_e_load_045() {
        let err = check_rule_against_manifest(
            &carrier_rule("(update-node (the NodeType/SOVEREIGN) social-class/wealth (add 5$))"),
            &manifest(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-045"));
    }

    /// D76's other half, in the bound checker: a queried type with no row
    /// carries the same code, because `ceiling(query)` is not computable
    /// without it.
    #[test]
    fn a_queried_type_with_no_manifest_row_is_e_load_045_in_the_bound_checker() {
        let err = super::cost("(fold sum (nodes NodeType/SOVEREIGN) it)").unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-045"));
    }

    /// D40's runtime half: a carrier the scenario forgot to hydrate fails
    /// loudly rather than reading as zero.
    #[test]
    fn an_unhydrated_carrier_is_e_eval_035() {
        assert_eq!(EvalCode::UnhydratedCarrier.spec_code(), "E-EVAL-035");
    }
}

// ====================================================== family 13 — C4
// The rule domain (§2.3) — what a rule fires over, and how many times.
//
// Runtime row deferred: `(domain :graph)` *firing exactly once* against a
// multi-node graph needs the tick loop's subject enumeration (D44). The
// static resolution that decides it is pinned here in full.
mod c4_rule_domain {
    use super::{e, vocabulary};
    use babylon_bsl::bindings::parse_bindings;
    use babylon_bsl::canonical_ast::canonical_bytes;
    use babylon_bsl::domain::{resolve_domain, DomainError, RuleDomain};
    use babylon_bsl::grammar::{check_enum_ref_kinds, check_graph_flag_placement};

    fn domain_of(body: &str) -> Result<RuleDomain, DomainError> {
        let form = e(&super::rule(body));
        let decls = parse_bindings(&form).expect("bindings must parse");
        resolve_domain(&form, &decls, &vocabulary())
    }

    /// §5.6's rule, unchanged, is an inferred node domain — the property
    /// D43 relies on to keep the pinned canonical bytes valid.
    #[test]
    fn the_worked_example_infers_a_node_domain_and_keeps_its_bytes() {
        let worked = "(rule demo/hunger \
             :material-basis \"subsistence deficit at the point of reproduction\" \
             :fuel 64 \
             (bindings (binding wealth :field social-class/wealth)) \
             (when (< wealth 1000.5$)) \
             (effects (update-node self social-class/agitation (add 0.05i))))";
        let form = e(worked);
        let decls = parse_bindings(&form).unwrap();
        assert_eq!(
            resolve_domain(&form, &decls, &vocabulary()),
            Ok(RuleDomain::Node("social-class".to_owned()))
        );
        assert_eq!(
            canonical_bytes(&form).unwrap().len(),
            421,
            "§5.6's bytes are unaffected: <domain> is optional and absent"
        );
    }

    /// `|U| = 0` — nothing is self-scoped.
    #[test]
    fn no_self_scoped_reference_and_no_domain_is_e_load_004() {
        let err = domain_of(
            "(bindings (binding now :tick)) (when (< now 5)) \
             (effects (emit EventType/RUPTURE (t now)))",
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-004"));
    }

    /// `|U| > 1` — two node types are.
    #[test]
    fn two_self_scoped_node_types_is_e_load_004() {
        let err = domain_of(
            "(bindings (binding wealth :field social-class/wealth) \
                       (binding claim :field organization/claim-strength)) \
             (when (< wealth claim)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-004"));
    }

    /// An explicit `<domain>` replaces the inference outright; the second
    /// type is then a foreign read, which is `E-TYPE-010` and not an
    /// ambiguity.
    #[test]
    fn an_explicit_domain_overrides_the_inference_and_disagreement_is_e_type_010() {
        let err = domain_of(
            "(domain NodeType/SOCIAL_CLASS) \
             (bindings (binding claim :field organization/claim-strength)) \
             (when (< claim 5)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-TYPE-010"));
    }

    /// D43's stated property, proved: a binding referenced only inside a
    /// fold body never enters `U`, so adding one cannot change how many
    /// times a rule fires.
    #[test]
    fn a_fold_scoped_binding_never_changes_the_firing_multiplicity() {
        assert_eq!(
            domain_of(
                "(domain :graph) \
                 (bindings (binding claim :field organization/claim-strength)) \
                 (when (< (fold sum (nodes NodeType/ORGANIZATION) claim) 5)) \
                 (effects (emit EventType/RUPTURE (x 1)))"
            ),
            Ok(RuleDomain::Graph)
        );
    }

    /// `self` is not bound in a graph-domain rule.
    #[test]
    fn self_in_a_graph_domain_rule_is_e_type_015() {
        let err = domain_of(
            "(domain :graph) (bindings) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-TYPE-015"));
    }

    /// …and neither is a `:field` binding read outside a query body.
    #[test]
    fn a_rule_scope_field_read_in_a_graph_domain_rule_is_e_type_015() {
        let err = domain_of(
            "(domain :graph) \
             (bindings (binding wealth :field social-class/wealth)) \
             (when (< wealth 5)) \
             (effects (emit EventType/RUPTURE (x 1)))",
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-TYPE-015"));
    }

    /// D42: `:graph` is a flag of the `domain` form and illegal elsewhere.
    #[test]
    fn graph_outside_a_domain_form_is_e_parse_013() {
        let err = check_graph_flag_placement(&e(&super::rule(
            "(bindings (binding g :metric density :graph)) \
             (effects (emit EventType/RUPTURE (x 1)))",
        )))
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-PARSE-013");
    }

    /// D74 at `domain`'s operand.
    #[test]
    fn a_domain_naming_an_edge_type_is_e_type_011() {
        let err = check_enum_ref_kinds(&e("(domain EdgeType/SOLIDARITY)")).unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-011");
    }

    /// §5.3 (D43): `<domain>` encodes in its grammar position, an enum-ref
    /// domain as one `atom enum` child and `(domain :graph)` as one `opt`
    /// form carrying the flag under D20 — the two shapes are distinct bytes
    /// and neither is a keyword in value position.
    #[test]
    fn both_domain_shapes_have_distinct_canonical_bytes() {
        let typed = canonical_bytes(&e("(domain NodeType/SOCIAL_CLASS)")).unwrap();
        let graph = canonical_bytes(&e("(domain :graph)")).unwrap();
        assert_ne!(typed, graph);
        // The flag encodes exactly as its explicit `#t` spelling (D20).
        assert_eq!(graph, canonical_bytes(&e("(domain :graph #t)")).unwrap());
    }
}

// ====================================================== family 16 — C7
// Computed bindings (§2.5's `:expr`), landed before C5 because §2.7's score
// classifier resolves a score written as a binding name through its
// declared source, which needs `BindSource::Expr` to exist. The rst's §7
// order is a dependency order; this is one it does not name.
mod c7_computed_bindings {
    use super::{bound, e};
    use babylon_bsl::bindings::{parse_bindings, BindSource};
    use babylon_bsl::evaluator::Value;
    use babylon_bsl::fuel::IntrinsicCosts;
    use babylon_bsl::intrinsic_host::EmptyIntrinsicHost;
    use babylon_bsl::rule_pipeline::resolve_expr_bindings;
    use babylon_kernel::Currency;
    use std::collections::HashMap;

    fn decls(bindings: &str) -> Vec<babylon_bsl::bindings::BindingDecl> {
        let form = e(&super::rule(&format!(
            "(bindings {bindings}) \
             (effects (update-node self social-class/agitation (add 0.05i)))"
        )));
        parse_bindings(&form).expect("bindings must parse")
    }

    fn binding_error(bindings: &str) -> Option<&'static str> {
        let form = e(&super::rule(&format!(
            "(bindings {bindings}) \
             (effects (update-node self social-class/agitation (add 0.05i)))"
        )));
        parse_bindings(&form).err().and_then(|e| e.spec_code())
    }

    /// §2.5's own worked example: a rule may name an intermediate value.
    #[test]
    fn an_expr_binding_names_a_computed_value() {
        let d = decls(
            "(binding wealth      :field social-class/wealth) \
             (binding subsistence :const vitality/subsistence-cost) \
             (binding drained     :expr (- wealth subsistence))",
        );
        assert!(matches!(d[2].source, BindSource::Expr(_)));
    }

    /// D49: resolution is in declaration order; a forward reference and a
    /// self-reference are both `E-PARSE-032`, so no cycle is expressible
    /// and nothing needs a cycle analysis.
    #[test]
    fn a_forward_or_self_reference_is_e_parse_032() {
        assert_eq!(
            binding_error(
                "(binding drained :expr (- wealth 1$)) \
                 (binding wealth  :field social-class/wealth)"
            ),
            Some("E-PARSE-032")
        );
        assert_eq!(
            binding_error("(binding loop :expr (+ loop 1))"),
            Some("E-PARSE-032")
        );
    }

    /// D49: `:optional`/`:default` on a `:expr` — a computed value is never
    /// absent, because its operands were resolved at load or the rule did
    /// not load.
    #[test]
    fn optional_or_default_on_an_expr_is_e_parse_033() {
        assert_eq!(
            binding_error("(binding d :expr (+ 1 2) :optional :default 0)"),
            Some("E-PARSE-033")
        );
        assert_eq!(
            binding_error("(binding d :expr (+ 1 2) :default 0)"),
            Some("E-PARSE-033")
        );
    }

    /// D50: `bound(rule)` gains `Σ cost(:expr bindings)`, and every other
    /// bind-src still contributes nothing — the property §5.6's pinned
    /// `bound = 7` rests on.
    #[test]
    fn only_expr_bindings_enter_the_static_bound() {
        let external = bound(&super::rule(
            "(bindings (binding wealth :field social-class/wealth) (binding now :tick)) \
             (when (< wealth 1000.5$)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        ));
        assert_eq!(external, Ok(7), "§5.6's worked bound, unmoved");
        // + cost((- wealth 1000.5$)) = 1 + 1 + 0 = 2.
        let computed = bound(&super::rule(
            "(bindings (binding wealth :field social-class/wealth) \
                       (binding drained :expr (- wealth 1000.5$))) \
             (when (< wealth 1000.5$)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        ));
        assert_eq!(computed, Ok(9));
    }

    /// §4.5's asymmetry, executed: the expression is charged **once** at
    /// binding time and each later reference charges a variable-reference 1,
    /// so the same algebra written twice inline costs strictly more.
    #[test]
    fn a_named_expression_costs_strictly_less_than_the_same_algebra_twice() {
        let costs = IntrinsicCosts::default();
        let supplied = |name: &str| {
            HashMap::from([(
                name.to_owned(),
                Value::Currency(Currency::from_micro_units(900_000_000)),
            )])
        };

        // Named once: charge the expression (1 + 1 + 0 = 2) at binding
        // time, then 1 per reference in the two comparisons below.
        let named = decls(
            "(binding wealth  :field social-class/wealth) \
             (binding drained :expr (- wealth 100$))",
        );
        let mut env = supplied("wealth");
        let mut fuel_named = 1_000;
        resolve_expr_bindings(
            &named,
            &mut env,
            &costs,
            &EmptyIntrinsicHost,
            &mut fuel_named,
        )
        .expect("the :expr must resolve");
        assert_eq!(1_000 - fuel_named, 2, "charged once, at binding time");
        assert!(env.contains_key("drained"));

        // Written inline twice, the same algebra is charged twice.
        let inline = decls(
            "(binding wealth :field social-class/wealth) \
             (binding a :expr (- wealth 100$)) \
             (binding b :expr (- wealth 100$))",
        );
        let mut env2 = supplied("wealth");
        let mut fuel_inline = 1_000;
        resolve_expr_bindings(
            &inline,
            &mut env2,
            &costs,
            &EmptyIntrinsicHost,
            &mut fuel_inline,
        )
        .expect("both :exprs must resolve");
        assert!(
            1_000 - fuel_inline > 1_000 - fuel_named,
            "restating the algebra costs strictly more (§4.5)"
        );
    }

    /// A `:expr` is evaluated at rule scope, so a foreign-node-type
    /// `:field` reference inside one is `E-TYPE-010` — the same rule as
    /// anywhere else at rule scope.
    #[test]
    fn a_foreign_field_inside_an_expr_is_e_type_010() {
        let form = e(&super::rule(
            "(bindings (binding claim :field organization/claim-strength) \
                       (binding doubled :expr (+ claim claim))) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        ));
        let d = parse_bindings(&form).unwrap();
        let err = babylon_bsl::scope::check_foreign_field_scoping(
            &form,
            &d,
            Some("social-class"),
            &super::vocabulary(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-010");
    }
}

// ============================================= family 22 (bindings half) — C13
// The calendar bind-srcs (§2.5, D68). The rest of family 22 — the intrinsic
// cap and the RNG carrier key — lands with C13 proper.
mod c13_calendar_bindings {
    use super::e;
    use babylon_bsl::bindings::{parse_bindings, BindSource};

    fn decls_of(bindings: &str) -> Result<Vec<babylon_bsl::bindings::BindingDecl>, &'static str> {
        let form = e(&super::rule(&format!(
            "(bindings {bindings}) \
             (effects (update-node self social-class/agitation (add 0.05i)))"
        )));
        parse_bindings(&form).map_err(|err| err.spec_code().unwrap_or("<uncoded>"))
    }

    /// D68: calendar reads are **bindings, not arithmetic** — a kernel
    /// seam, which is the category R10 sanctions without a rider. No `mod`
    /// and no `floor-div` arrive behind them.
    #[test]
    fn the_three_calendar_bind_srcs_parse_and_bind_int() {
        let d = decls_of(
            "(binding y :year) (binding toy :tick-of-year) (binding phase :tick-in-cycle 52)",
        )
        .expect("the calendar bind-srcs are §2.5 productions");
        assert_eq!(d[0].source, BindSource::Year);
        assert_eq!(d[1].source, BindSource::TickOfYear);
        assert_eq!(d[2].source, BindSource::TickInCycle(52));
    }

    /// §1.6: the cycle length must be `> 0`.
    #[test]
    fn a_zero_or_negative_cycle_length_is_e_parse_014() {
        assert_eq!(decls_of("(binding p :tick-in-cycle 0)"), Err("E-PARSE-014"));
        assert_eq!(
            decls_of("(binding p :tick-in-cycle -4)"),
            Err("E-PARSE-014")
        );
    }

    /// D68's bound, stated precisely: the length is a **literal**, so the
    /// value is a static function of the tick and the content bytes — an
    /// expression there is not expressible, which is what stops a general
    /// mod operator over arbitrary expressions arriving behind the seam.
    #[test]
    fn a_computed_cycle_length_is_not_expressible() {
        assert!(decls_of("(binding p :tick-in-cycle (+ 26 26))").is_err());
    }
}

// ====================================================== family 14 — C5
// Element selection (§2.7's `select-max` / `select-min`).
//
// Runtime rows deferred: the tie vector, the `E-EVAL-021` empty query, and
// a selection feeding `update-node`/`field-of` all need the query
// evaluator. The result-type rule, the score rule and the cost row are
// pinned statically, and the tiebreak is pinned as language text below.
mod c5_element_selection {
    use super::{cost, e, type_env};
    use babylon_bsl::bindings::parse_bindings;
    use babylon_bsl::evaluator::EvalCode;
    use babylon_bsl::score_class::{selection_result_class, ScoreClass};
    use babylon_bsl::typecheck::{check_selection_scores, TypeCode};

    fn score_error(body: &str) -> Option<TypeCode> {
        let form = e(&super::rule(body));
        let decls = parse_bindings(&form).expect("bindings must parse");
        check_selection_scores(&form, &type_env(), &decls)
            .err()
            .and_then(|err| err.code)
    }

    /// §2.7: the result type is the query's ELEMENT type — `NodeRef` for
    /// `nodes`/`neighbors`/`members-of`, `EdgeRef` for `edges`,
    /// `HyperedgeRef` for `hyperedges`/`hyperedges-of`. All six heads.
    #[test]
    fn the_result_type_is_the_querys_element_type_for_all_six_heads() {
        let cases = [
            ("(nodes NodeType/SOCIAL_CLASS)", ScoreClass::NodeReference),
            (
                "(neighbors self EdgeType/SOLIDARITY :out NodeType/SOCIAL_CLASS)",
                ScoreClass::NodeReference,
            ),
            (
                "(members-of h HyperedgeType/COMMUNITY)",
                ScoreClass::NodeReference,
            ),
            ("(edges EdgeType/SOLIDARITY)", ScoreClass::EdgeReference),
            (
                "(hyperedges HyperedgeType/COMMUNITY)",
                ScoreClass::HyperedgeReference,
            ),
            (
                "(hyperedges-of self HyperedgeType/COMMUNITY)",
                ScoreClass::HyperedgeReference,
            ),
        ];
        for (query, expected) in cases {
            assert_eq!(selection_result_class(&e(query)), expected, "{query}");
        }
    }

    /// D46: the score must be a comparable scalar. A `Bool` and an
    /// `Enum<T>` score are `E-TYPE-016`.
    #[test]
    fn a_bool_or_enum_score_is_e_type_016() {
        assert_eq!(
            score_error(
                "(bindings) (effects (update-node \
                 (select-max (nodes NodeType/ORGANIZATION) (< 1 2)) \
                 social-class/agitation (add 0.05i)))"
            ),
            Some(TypeCode::NonComparableScore)
        );
        assert_eq!(
            score_error(
                "(bindings) (effects (update-node \
                 (select-min (nodes NodeType/ORGANIZATION) NodeType/POLITY) \
                 social-class/agitation (add 0.05i)))"
            ),
            Some(TypeCode::NonComparableScore)
        );
        // A reference score is rejected for the same reason: there is no
        // ordering on references in the language (D67).
        assert_eq!(
            score_error(
                "(bindings) (effects (update-node \
                 (select-max (nodes NodeType/ORGANIZATION) it) \
                 social-class/agitation (add 0.05i)))"
            ),
            Some(TypeCode::NonComparableScore)
        );
    }

    /// D46's other half, proved by acceptance: **kind is unconstrained on
    /// the score**. `organization/claim-strength` is declared intensive and
    /// ranking by it must ACCEPT — §3.4 polices aggregation, and ordering
    /// aggregates nothing, so the weighted-mean obligation has nothing to
    /// attach to.
    #[test]
    fn an_intensive_score_accepts_because_ordering_is_not_aggregation() {
        assert_eq!(
            score_error(
                "(bindings) (effects (update-node \
                 (select-max (nodes NodeType/ORGANIZATION) \
                             (field-of it organization/claim-strength)) \
                 social-class/agitation (add 0.05i)))"
            ),
            None
        );
    }

    /// §3.7's row: `2 + cost(query) + ceiling(query) × cost(score)` — the
    /// same shape as a fold with one body and no weight.
    #[test]
    fn a_selection_costs_two_plus_query_plus_ceiling_times_score() {
        // 2 + query(1) + 40 × field-of(2) = 83.
        assert_eq!(
            cost(
                "(select-max (nodes NodeType/ORGANIZATION) \
                 (field-of it organization/claim-strength))"
            ),
            Ok(83)
        );
        // Named with `:as`: `cost(:as name) = 0` (§3.7), so the bound is
        // unchanged — a reference to the name would cost 1 like any other.
        assert_eq!(
            cost(
                "(select-max (nodes NodeType/ORGANIZATION) :as winner \
                 (field-of winner organization/claim-strength))"
            ),
            Ok(83)
        );
    }

    /// D45: the tiebreak is a property of the LANGUAGE, not of each rule —
    /// the first element in §2.6's ascending id byte order wins, for both
    /// operators. Pinned here as the identity of the empty-query code and
    /// re-proved as behaviour when the query evaluator lands.
    #[test]
    fn an_empty_selection_shares_the_empty_aggregate_code() {
        assert_eq!(EvalCode::EmptyAggregate.spec_code(), "E-EVAL-021");
    }
}

// ====================================================== family 15 — C6
// Effect-position iteration (§2.8's `for-each`).
//
// Runtime rows deferred and named: the per-element `update-edge`/`emit`
// results, the pre-state materialization proof, and the empty-query
// no-op all need the query evaluator. The grammar, the arity, the static
// bound and the `E-LOAD-040` interaction are pinned.
mod c6_effect_position_iteration {
    use super::{bound, cost};

    /// §3.7's row: `2 + cost(query) + ceiling(query) × Σ cost(effect-items)`
    /// — charged exactly as `exists`/`forall` are, which is what keeps the
    /// totality argument syntactic rather than analysed.
    #[test]
    fn for_each_is_charged_like_exists_and_forall() {
        // 2 + query(1) + 40 × update-edge(3 + 1 + 0 + (1 + 0)) = 203.
        assert_eq!(
            cost(
                "(for-each (edges EdgeType/SOLIDARITY) \
                 (update-edge it solidarity/strength (scale 0.95c)))"
            ),
            Ok(203)
        );
    }

    /// The §2.8 worked shape: two effect items per element, both inside the
    /// one ceiling factor.
    #[test]
    fn the_body_is_summed_inside_the_single_ceiling_factor() {
        // update-edge(5) + emit(3 + field-of(2)) = 10; 2 + 1 + 40 × 10 = 403.
        assert_eq!(
            cost(
                "(for-each (edges EdgeType/SOLIDARITY) \
                 (update-edge it solidarity/strength (scale 0.95c)) \
                 (emit EventType/RUPTURE (strength (field-of it solidarity/strength))))"
            ),
            Ok(403)
        );
    }

    /// Nested `for-each` composes the same way, and its static bound is the
    /// product of the two ceilings — bounded, not a loop.
    #[test]
    fn nested_for_each_multiplies_its_two_ceilings() {
        // inner: 2 + 1 + 40 × 5 = 203; outer: 2 + 1 + 100 × 203 = 20303.
        assert_eq!(
            cost(
                "(for-each (nodes NodeType/SOCIAL_CLASS) \
                 (for-each (edges EdgeType/SOLIDARITY) \
                  (update-edge it solidarity/strength (scale 0.95c))))"
            ),
            Ok(20_303)
        );
    }

    /// A `for-each` one short of its static bound is rejected at LOAD
    /// (`E-LOAD-040`), which is the whole point of §3.7 being static.
    #[test]
    fn a_for_each_one_short_of_its_bound_is_e_load_040() {
        use babylon_bsl::bound_checker::check_rule;
        use babylon_bsl::fuel::IntrinsicCosts;
        let body = "(bindings) (effects (for-each (edges EdgeType/SOLIDARITY) \
                    (update-edge it solidarity/strength (scale 0.95c))))";
        let starved =
            format!("(rule demo/r9 :material-basis \"the wage relation\" :fuel 202 {body})");
        let err = check_rule(
            &super::e(&starved),
            &super::ceilings(),
            &IntrinsicCosts::default(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-040"));
        // …and one MORE than the bound loads (§4.5's off-by-one: budget
        // `bound + 1`, because the meter must stay strictly positive).
        let funded =
            format!("(rule demo/r9 :material-basis \"the wage relation\" :fuel 204 {body})");
        assert_eq!(
            check_rule(
                &super::e(&funded),
                &super::ceilings(),
                &IntrinsicCosts::default()
            ),
            Ok(203)
        );
    }

    /// The bound composes through a rule: `bound(rule)` sums its effect
    /// items, so a `for-each` is simply one of them.
    #[test]
    fn a_for_each_enters_bound_rule_as_one_effect_item() {
        assert_eq!(
            bound(&super::rule(
                "(bindings) (effects \
                 (for-each (edges EdgeType/SOLIDARITY) \
                  (update-edge it solidarity/strength (scale 0.95c))))"
            )),
            Ok(203)
        );
    }
}

// ====================================================== family 17 — C8
// Typed neighbours and element naming (§2.6).
//
// **The first `neighbors` vectors this document has ever required** — the
// reference's own words. D51 makes the result `NodeType` a mandatory fourth
// operand, a breaking change to a form no vector and no content rule
// exercised, and this crate's bound checker is the one place that carried
// the pre-change spelling.
//
// Runtime row deferred: the **multiplicity vector** (two qualifying edges
// reaching one node, whose `fold count` must be 1) is D72's set semantics,
// which needs the query evaluator. It is named here, not skipped.
mod c8_typed_neighbours_and_naming {
    use super::{cost, e};
    use babylon_bsl::grammar::{check_arities_and_closed_sets, check_enum_ref_kinds};
    use babylon_bsl::scope::check_element_names;

    /// D51: the operand is **mandatory**, so the pre-C8 three-operand form
    /// is an arity error rather than a silently edge-type-only bound.
    #[test]
    fn a_three_operand_neighbors_is_e_parse_042() {
        let err = check_arities_and_closed_sets(&e("(neighbors self EdgeType/SOLIDARITY :out)"))
            .unwrap_err();
        assert_eq!(err.spec_code(), "E-PARSE-042");
        assert!(check_arities_and_closed_sets(&e(
            "(neighbors self EdgeType/SOLIDARITY :out NodeType/SOCIAL_CLASS)"
        ))
        .is_ok());
    }

    /// D74: swapping the two operands is `E-TYPE-011` at both positions.
    #[test]
    fn the_two_operands_swapped_is_e_type_011() {
        let err = check_enum_ref_kinds(&e(
            "(neighbors self NodeType/SOCIAL_CLASS :out EdgeType/SOLIDARITY)",
        ))
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-011");
    }

    /// D52: `ceiling(neighbors)` is the **lesser** of the two ceilings —
    /// neither bound can be exceeded, so the smaller is the honest one, and
    /// the mandatory operand is what makes the second number available.
    #[test]
    fn the_static_bound_is_the_lesser_of_the_two_ceilings() {
        // EdgeType/SOLIDARITY 40 < NodeType/SOCIAL_CLASS 100 → 40.
        // 2 + query(1 + self) + 40 × 1 = 44.
        assert_eq!(
            cost("(fold sum (neighbors self EdgeType/SOLIDARITY :out NodeType/SOCIAL_CLASS) it)"),
            Ok(44)
        );
        // NodeType/ORGANIZATION 40 vs EdgeType/IN_SCALE 5000 → 40, so the
        // annotation TIGHTENS what the pre-C8 reading would have bounded.
        assert_eq!(
            cost("(fold sum (neighbors self EdgeType/IN_SCALE :in NodeType/ORGANIZATION) it)"),
            Ok(44)
        );
    }

    /// §2.5's foreign-field rule now applies through `neighbors` exactly as
    /// it does through `nodes`: the annotated type legalises its own fields
    /// inside the body. Six systems need exactly this read.
    #[test]
    fn a_fold_body_over_neighbors_legalises_the_annotated_types_fields() {
        use babylon_bsl::bindings::parse_bindings;
        use babylon_bsl::scope::check_foreign_field_scoping;
        let form = e(&super::rule(
            "(bindings (binding claim :field organization/claim-strength)) \
             (when (< (fold mean (neighbors self EdgeType/SOLIDARITY :in \
                                   NodeType/ORGANIZATION) claim) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        ));
        let decls = parse_bindings(&form).unwrap();
        assert_eq!(
            check_foreign_field_scoping(&form, &decls, Some("social-class"), &super::vocabulary()),
            Ok(())
        );
    }

    /// D54: `:as` names the element, and the name shares the rule's binding
    /// namespace — `:as it`/`:as self` is `E-PARSE-022` and a collision with
    /// a binding is `E-PARSE-030`.
    #[test]
    fn as_it_and_as_self_are_e_parse_022_and_a_collision_is_e_parse_030() {
        for reserved in ["it", "self"] {
            let form = e(&super::rule(&format!(
                "(bindings) (when (exists (nodes NodeType/ORGANIZATION) :as {reserved} #t)) \
                 (effects (update-node self social-class/agitation (add 0.05i)))"
            )));
            let err = check_element_names(&form, &[]).unwrap_err();
            assert_eq!(err.spec_code(), "E-PARSE-022", "{reserved}");
        }
        let form = e(&super::rule(
            "(bindings (binding sector :field social-class/wealth)) \
             (when (exists (hyperedges HyperedgeType/ECONOMIC_SECTOR) :as sector #t)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        ));
        let err = check_element_names(&form, &["sector".to_owned()]).unwrap_err();
        assert_eq!(err.spec_code(), "E-PARSE-030");
    }

    /// D53 + D54: `it` denotes the **innermost** element and `:as` reaches
    /// the outer one — §2.6's own two-hop example, which accepts, and its
    /// static bound, `2 + 1 + 500 × (2 + 32 × 2) = 33503`.
    #[test]
    fn the_two_hop_nested_fold_accepts_and_bounds() {
        let source = "(fold sum (hyperedges HyperedgeType/ECONOMIC_SECTOR) :as sector \
             (fold sum (members-of sector HyperedgeType/ECONOMIC_SECTOR) \
                   (field-of it social-class/wealth)))";
        assert_eq!(
            check_element_names(
                &e(&super::rule(&format!(
                    "(bindings) (when (< {source} 5)) \
                     (effects (update-node self social-class/agitation (add 0.05i)))"
                ))),
                &[]
            ),
            Ok(())
        );
        // inner: 2 + query(1 + sector ref 1) + 32 × field-of(2) = 68;
        // outer: 2 + query(1) + 500 × 68 = 34003.
        assert_eq!(cost(source), Ok(34_003));
    }

    /// D54: a `:as` name referenced outside its body is `E-TYPE-012` — and
    /// `cost(:as name) = 0` while a *reference* to it costs 1, which the
    /// C5 vector already pinned.
    #[test]
    fn it_outside_every_body_is_e_type_012() {
        let form = e(&super::rule(
            "(bindings) (when (< it 5)) \
             (effects (update-node self social-class/agitation (add 0.05i)))",
        ));
        let err = check_element_names(&form, &[]).unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-012");
    }
}

// ====================================================== family 18 — C9
// Metric registration (§2.11).
//
// Runtime rows deferred: `E-EVAL-036` (a `metric-of` against a referent of
// another type) and `E-EVAL-037` (a value the provider did not produce)
// need the provider seam and the query evaluator; their codes are pinned.
// The **stability vector** — two rules at one anchor reading one metric,
// whose values must be equal — is a determinism obligation on the
// *provider* (§2.11's list), enforced by review and by the determinism
// contract's golden vectors, and is recorded there rather than faked here.
mod c9_metric_registration {
    use super::{cost, e};
    use babylon_bsl::bindings::parse_bindings;
    use babylon_bsl::canonical_ast::canonical_bytes;
    use babylon_bsl::evaluator::EvalCode;
    use babylon_bsl::metrics::{MetricDomain, MetricRegistry};
    use babylon_bsl::typecheck::{typecheck_aggregation, TypeCode, TypeEnv};
    use std::collections::HashMap;

    const GRAPH: &str = "(metric solidarity-density :type coefficient :kind intensive \
        (domain :graph) :provider topology-scores)";
    const ELEMENT: &str = "(metric betweenness-centrality :type coefficient :kind intensive \
        (domain NodeType/ORGANIZATION) :provider topology-scores)";

    fn registry() -> MetricRegistry {
        let mut r = MetricRegistry::default();
        r.declare(&e(GRAPH)).expect("graph metric");
        r.declare(&e(ELEMENT)).expect("element metric");
        r
    }

    fn reading(body: &str) -> Option<&'static str> {
        let form = e(&super::rule(body));
        let decls = parse_bindings(&form).expect("bindings must parse");
        registry()
            .check_reading_forms(&form, &decls)
            .err()
            .and_then(|err| err.spec_code())
    }

    /// §2.11's two domains, and D56's ruling that the element-indexed one
    /// is read by the **accessor** rather than by a `:metric-of` bind-src.
    #[test]
    fn a_graph_metric_binds_and_an_element_metric_is_accessed() {
        let r = registry();
        assert_eq!(
            r.get("solidarity-density").unwrap().domain,
            MetricDomain::Graph
        );
        assert_eq!(
            r.get("betweenness-centrality").unwrap().domain,
            MetricDomain::Element("organization".to_owned())
        );
        assert_eq!(
            reading(
                "(bindings (binding d :metric solidarity-density) \
                           (binding c :expr (metric-of self betweenness-centrality))) \
                 (effects (update-node self social-class/agitation (add 0.05i)))"
            ),
            None
        );
    }

    /// Reading either through the other's form is `E-LOAD-012` — both
    /// static, because the declaration and the reading form are both
    /// content.
    #[test]
    fn each_read_through_the_wrong_form_is_e_load_012() {
        assert_eq!(
            reading(
                "(bindings (binding c :metric betweenness-centrality)) \
                 (effects (update-node self social-class/agitation (add 0.05i)))"
            ),
            Some("E-LOAD-012")
        );
        assert_eq!(
            reading(
                "(bindings (binding d :expr (metric-of self solidarity-density))) \
                 (effects (update-node self social-class/agitation (add 0.05i)))"
            ),
            Some("E-LOAD-012")
        );
    }

    /// §6.3's correction, re-proved for **both** reading forms: an
    /// unregistered name is `E-LOAD-011`, never `0.0`.
    #[test]
    fn an_unregistered_name_is_e_load_011_through_both_forms() {
        assert_eq!(
            reading(
                "(bindings (binding x :metric nowhere)) \
                 (effects (update-node self social-class/agitation (add 0.05i)))"
            ),
            Some("E-LOAD-011")
        );
        assert_eq!(
            reading(
                "(bindings (binding x :expr (metric-of self nowhere))) \
                 (effects (update-node self social-class/agitation (add 0.05i)))"
            ),
            Some("E-LOAD-011")
        );
    }

    /// D55: a declaration disagreeing with the kernel's registration.
    #[test]
    fn kernel_disagreement_is_e_load_025() {
        let r = registry();
        let mut registered = r.get("solidarity-density").unwrap().clone();
        registered.provider = "somewhere-else".to_owned();
        let kernel = HashMap::from([("solidarity-density".to_owned(), registered)]);
        assert_eq!(
            r.check_against_kernel(&kernel).unwrap_err().spec_code(),
            Some("E-LOAD-025")
        );
    }

    /// D55 supersedes D12's metric clause: the **declared** kind
    /// propagates, so an intensive metric feeding an unweighted `mean` is
    /// `E-TYPE-042` exactly as an intensive field is.
    #[test]
    fn the_declared_kind_propagates_into_the_aggregation_law() {
        let mut fields = HashMap::new();
        registry().merge_into_kind_env(&mut fields);
        let env = TypeEnv {
            fields,
            exemptions: &[],
        };
        assert_eq!(
            typecheck_aggregation(&e("(mean solidarity-density)"), &env)
                .unwrap_err()
                .code,
            Some(TypeCode::UnweightedMeanOfIntensive)
        );
    }

    /// D57: the READ costs `1 + cost(operand)` like any other accessor.
    /// The provider's computation is not metered against the reading rule —
    /// a rule cannot bound a betweenness computation, and pretending
    /// otherwise would put a number in `:fuel` that means nothing.
    #[test]
    fn a_metric_read_costs_one_plus_its_operand_and_never_the_provider() {
        assert_eq!(cost("(metric-of self betweenness-centrality)"), Ok(2));
        assert_eq!(
            cost("(metric-of (the NodeType/POLITY) betweenness-centrality)"),
            Ok(2)
        );
    }

    /// §5.5: a `metric` form hashes into its own digest like
    /// `deffield`/`intrinsic`/`manifest`, under both `<domain>` shapes, and
    /// the two shapes are distinct bytes.
    #[test]
    fn both_domain_shapes_have_distinct_canonical_bytes() {
        let graph = canonical_bytes(&e(GRAPH)).unwrap();
        let element = canonical_bytes(&e(ELEMENT)).unwrap();
        assert_ne!(graph, element);
        assert!(!graph.is_empty() && !element.is_empty());
    }

    /// §2.11's two runtime disciplines, pinned as codes: absence is never a
    /// zero, at either failure.
    #[test]
    fn the_two_runtime_metric_failures_have_their_own_codes() {
        assert_eq!(EvalCode::MetricDomainMismatch.spec_code(), "E-EVAL-036");
        assert_eq!(EvalCode::MetricValueAbsent.spec_code(), "E-EVAL-037");
    }
}
