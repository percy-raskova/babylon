//! `membership-field-of` through the composed rule pipeline (§2.10, D81; §3.4): a fold may read a
//! membership's payload, and the declaration's kind reaches the aggregation law. The evaluator's
//! runtime rows (each scalar type, the refusals, the order) live in `evaluator.rs`.

use babylon_bsl::bindings::BindingVocabulary;
use babylon_bsl::declarations::FieldRegistry;
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::reader;
use babylon_bsl::rule_pipeline::{self, LoadContext};
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::EnumRegistry;
use babylon_bsl::vocabulary::{ClosedVocabulary, EnumKind};
use std::collections::{HashMap, HashSet};

fn vocabulary() -> ClosedVocabulary {
    ClosedVocabulary::new([
        (EnumKind::NodeType, vec!["SOCIAL_CLASS".to_owned()]),
        (EnumKind::HyperedgeType, vec!["NATION".to_owned()]),
        (EnumKind::EventType, vec!["RUPTURE".to_owned()]),
    ])
    .expect("the fixture vocabulary is disjoint")
}

/// The spec code `load_rule` reports for `body`, or `None` if the rule loads.
fn load_code(body: &str) -> Option<&'static str> {
    let v = vocabulary();
    let enums = EnumRegistry::default();
    let mut registry = FieldRegistry::default();
    for source in [
        "(deffield nation/share :type probability :kind intensive :member NodeType/SOCIAL_CLASS)",
        "(deffield nation/households :type int :kind extensive :member NodeType/SOCIAL_CLASS)",
    ] {
        registry
            .declare(&reader::read(source).expect("parses").0, &v, &enums)
            .expect(source);
    }
    let types = TypeEnv {
        membership_fields: registry.type_env_membership_fields(),
        fields: registry.type_env_fields(),
        exemptions: &[],
    };
    let ceilings = CardinalityCeilings::new(
        HashMap::from([
            ("NodeType/SOCIAL_CLASS".to_owned(), 100),
            ("HyperedgeType/NATION".to_owned(), 10),
        ]),
        HashMap::from([("HyperedgeType/NATION".to_owned(), 32)]),
    );
    let intrinsics = IntrinsicCosts::default();
    let systems: HashSet<String> = HashSet::from(["demo".to_owned()]);
    let const_values = HashMap::new();
    let vocab = BindingVocabulary {
        fields: types.fields.keys().cloned().collect(),
        consts: HashSet::new(),
        probability_consts: HashSet::new(),
        metrics: HashSet::new(),
    };
    let ctx = LoadContext {
        vocabulary: &vocab,
        types: &types,
        enums: &enums,
        const_values: &const_values,
        ceilings: &ceilings,
        intrinsics: &intrinsics,
        systems: &systems,
        vocabulary_registry: Some(&v),
        rule_file: "tests/membership_field_of.rs",
    };
    let source = format!(
        "(rule demo/m :role mechanic :evidence derived :material-basis \"the nation\" \
         :fuel 65536 {body})"
    );
    match rule_pipeline::load_rule(&source, &ctx) {
        Ok(_) => None,
        Err(err) => Some(err.spec_code().unwrap_or("<uncoded>")),
    }
}

#[test]
fn a_mean_over_members_reading_a_payload_needs_a_weight() {
    // An intensive payload under an unweighted `mean` is the recorded variance error.
    assert_eq!(
        load_code(
            "(domain :graph) (bindings) \
             (when (< (fold max (hyperedges HyperedgeType/NATION) :as h \
                        (fold mean (members-of h HyperedgeType/NATION) \
                              (membership-field-of h it nation/share))) 0.5i)) \
             (effects (emit EventType/RUPTURE (x 1)))"
        ),
        Some("E-TYPE-042")
    );
    // With an extensive weight it loads.
    assert_eq!(
        load_code(
            "(domain :graph) (bindings) \
             (when (< (fold max (hyperedges HyperedgeType/NATION) :as h \
                        (fold mean (members-of h HyperedgeType/NATION) \
                              (membership-field-of h it nation/share) \
                              :weight (membership-field-of h it nation/households))) 0.5i)) \
             (effects (emit EventType/RUPTURE (x 1)))"
        ),
        None
    );
}
