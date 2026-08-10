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
