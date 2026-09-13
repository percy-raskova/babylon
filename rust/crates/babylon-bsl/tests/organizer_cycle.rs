//! Organizer execution requires a closed, role-specific scheduled operation.

use babylon_bsl::bindings::BindingVocabulary;
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::rule_pipeline::{load_rule, LoadContext, LoadError, LoadedRule, RuleExecution};
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::EnumRegistry;
use std::collections::{HashMap, HashSet};

fn source(operation: &str, role: &str, position: &str) -> String {
    format!(
        "(rule organizer/{operation} :role {role} :evidence designed \
         :material-basis \"Resolve captured commitments and earned reports.\" \
         :fuel 1000000 (anchor :{position} ooda) ({operation}))"
    )
}

fn load(source: &str) -> Result<LoadedRule, LoadError> {
    load_rule(
        source,
        &LoadContext {
            vocabulary: &BindingVocabulary::default(),
            types: &TypeEnv {
                fields: HashMap::new(),
                exemptions: &[],
            },
            enums: &EnumRegistry::default(),
            const_values: &HashMap::new(),
            ceilings: &CardinalityCeilings::new(HashMap::new(), HashMap::new()),
            intrinsics: &IntrinsicCosts::default(),
            systems: &HashSet::from(["ooda".to_owned(), "metabolism".to_owned()]),
            vocabulary_registry: None,
            rule_file: "organizer-cycle.bsl",
        },
    )
}

#[test]
fn organizer_operations_load_only_as_explicit_native_execution() {
    for (operation, role, position) in [
        ("organizer-products", "mechanic", "before"),
        ("organizer-practice", "intent", "after"),
    ] {
        let rule = load(&source(operation, role, position)).expect("governed organizer operation");
        assert_ne!(rule.execution, RuleExecution::Graph);
        assert_eq!(rule.static_bound, 1_000_000);
        assert!(rule.bindings.is_empty());
        assert!(rule.domain.is_none());
    }
}

#[test]
fn organizer_native_bodies_are_not_certified_by_a_graph_only_synthetic_audit() {
    for (operation, role, position) in [
        ("organizer-products", "mechanic", "before"),
        ("organizer-practice", "intent", "after"),
    ] {
        let loaded = load(&source(operation, role, position)).unwrap();
        assert_eq!(
            babylon_bsl::sfs_profile::audit_rule_footprint(
                &loaded.rule,
                &babylon_bsl::vocabulary::ClosedVocabulary::default(),
                &CardinalityCeilings::new(HashMap::new(), HashMap::new()),
                &IntrinsicCosts::default(),
                &[],
            )
            .unwrap_err(),
            babylon_bsl::sfs_profile::SfsProfileError::NativeMaterialCycleUnsupported
        );
    }
}

#[test]
fn organizer_operations_refuse_nested_extra_or_wrong_role_execution() {
    for (operation, role, position) in [
        ("organizer-products", "mechanic", "before"),
        ("organizer-practice", "intent", "after"),
    ] {
        let original = source(operation, role, position);
        for replacement in [
            format!("(effects ({operation}))"),
            format!("({operation} 1)"),
            format!("({operation}) ({operation})"),
            format!("(when #t) ({operation})"),
        ] {
            assert!(load(&original.replace(&format!("({operation})"), &replacement)).is_err());
        }
        assert!(load(&original.replace(":fuel 1000000", ":fuel 999999")).is_err());
        assert!(load(&original.replace("ooda", "metabolism")).is_err());
        assert!(load(&original.replace(&format!(":role {role}"), ":role external-event")).is_err());
    }
    assert!(load(
        &source("organizer-practice", "intent", "after")
            .replace("organizer/organizer-practice", "unapproved/practice")
    )
    .is_err());
}
