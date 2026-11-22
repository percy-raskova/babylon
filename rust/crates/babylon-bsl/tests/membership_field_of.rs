//! `membership-field-of` through the composed rule pipeline (§2.10, D81; §3.4): a fold may read a
//! membership's payload, and the declaration's kind reaches the aggregation law. The evaluator's
//! runtime rows (each scalar type, the refusals, the order) live in `evaluator.rs`.

use babylon_bsl::bindings::BindingVocabulary;
use babylon_bsl::declarations::{self, FieldRegistry};
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
    let mut enums = EnumRegistry::default();
    declarations::parse_defenum(
        &reader::read("(defenum Tier (LOW HIGH))").expect("parses").0,
        &mut enums,
    )
    .expect("the fixture enum declares");
    let mut registry = FieldRegistry::default();
    for source in [
        "(deffield nation/tier :type enum :enum-type Tier :member NodeType/SOCIAL_CLASS)",
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

#[test]
fn a_rule_using_update_membership_loads() {
    // The verb is served (#653): it no longer stops at the load layer, and a nested one is
    // bounded like the other update verbs.
    assert_eq!(
        load_code(
            "(domain :graph) (bindings) \
             (effects (for-each (hyperedges HyperedgeType/NATION) :as h \
                (for-each (members-of h HyperedgeType/NATION) :as m \
                  (update-membership h m nation/share (set 0.5p)))))"
        ),
        None
    );
    // A fifth update-op head is still E-PARSE-015, read at the verb's own fourth operand.
    assert_eq!(
        load_code(
            "(domain :graph) (bindings) \
             (effects (for-each (hyperedges HyperedgeType/NATION) :as h \
                (for-each (members-of h HyperedgeType/NATION) :as m \
                  (update-membership h m nation/share (unset 0.5p)))))"
        ),
        Some("E-PARSE-015")
    );
}

#[test]
fn an_enum_membership_field_cannot_score_a_selection() {
    // D46 / E-TYPE-016: ranking by an enum-typed payload is refused at load, as `field-of` is.
    assert_eq!(
        load_code(
            "(domain :graph) (bindings) \
             (effects (for-each (hyperedges HyperedgeType/NATION) :as h \
                (update-membership h \
                  (select-max (members-of h HyperedgeType/NATION) \
                              (membership-field-of h it nation/tier)) \
                  nation/share (set 0.5p))))"
        ),
        Some("E-TYPE-016")
    );
    // The same rule scored by a numeric payload loads.
    assert_eq!(
        load_code(
            "(domain :graph) (bindings) \
             (effects (for-each (hyperedges HyperedgeType/NATION) :as h \
                (update-membership h \
                  (select-max (members-of h HyperedgeType/NATION) \
                              (membership-field-of h it nation/households)) \
                  nation/share (set 0.5p))))"
        ),
        None
    );
}

#[test]
fn arithmetic_mixing_an_intensive_and_an_extensive_membership_field_is_e_type_040() {
    let rule = |lhs: &str, rhs: &str| {
        format!(
            "(domain :graph) (bindings) \
             (effects (for-each (hyperedges HyperedgeType/NATION) :as h \
                (for-each (members-of h HyperedgeType/NATION) :as m \
                  (update-membership h m nation/households \
                    (set (+ (membership-field-of h m {lhs}) \
                            (membership-field-of h m {rhs})))))))"
        )
    };
    assert_eq!(
        load_code(&rule("nation/share", "nation/households")),
        Some("E-TYPE-040")
    );
    assert_eq!(
        load_code(&rule("nation/households", "nation/households")),
        None
    );
}

#[test]
fn a_membership_form_naming_an_undeclared_qname_is_refused_at_load() {
    // Both forms are served, so neither may let a qname declared nowhere through.
    let read = load_code(
        "(domain :graph) (bindings) \
         (when (< (fold max (hyperedges HyperedgeType/NATION) :as h \
                    (fold max (members-of h HyperedgeType/NATION) \
                          (membership-field-of h it nation/nowhere))) 5)) \
         (effects (emit EventType/RUPTURE (x 1)))",
    );
    let write = load_code(
        "(domain :graph) (bindings) \
         (effects (for-each (hyperedges HyperedgeType/NATION) :as h \
            (for-each (members-of h HyperedgeType/NATION) :as m \
              (update-membership h m nation/nowhere (set 1)))))",
    );

    // Neither form has a spec code for this: both are the typechecker's unknown-field
    // refusal, which is uncoded (the same one `field-of` gets inside a fold).
    assert_eq!(read, Some("<uncoded>"), "membership-field-of");
    assert_eq!(write, Some("<uncoded>"), "update-membership");
    // Outside a fold the read is refused too.
    assert_eq!(
        load_code(
            "(domain :graph) (bindings) \
             (effects (for-each (hyperedges HyperedgeType/NATION) :as h \
                (for-each (members-of h HyperedgeType/NATION) :as m \
                  (update-membership h m nation/households \
                    (set (membership-field-of h m nation/nowhere))))))"
        ),
        Some("<uncoded>")
    );
}
