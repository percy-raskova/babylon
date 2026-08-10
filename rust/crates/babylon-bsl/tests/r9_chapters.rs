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
