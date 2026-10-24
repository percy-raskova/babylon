//! Organizer execution requires a closed, role-specific scheduled operation.

use babylon_bsl::bindings::BindingVocabulary;
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::EmptyIntrinsicHost;
use babylon_bsl::rule_pipeline;
use babylon_bsl::rule_pipeline::{LoadContext, LoadError, LoadedRule, RuleExecution};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick;
use babylon_bsl::tick::DefinesEnv;
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::EnumRegistry;
use babylon_bsl::vocabulary::ClosedVocabulary;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::stable_element::StableElementResolver;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId, RngSeedContext};
use std::collections::{HashMap, HashSet};

fn source(operation: &str, role: &str, position: &str) -> String {
    format!(
        "(rule organizer/{operation} :role {role} :evidence designed \
         :material-basis \"Resolve captured commitments and earned reports.\" \
         :fuel 1000000 (anchor :{position} ooda) ({operation}))"
    )
}

fn load(source: &str) -> Result<LoadedRule, LoadError> {
    rule_pipeline::load_rule(
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
fn organizer_graph_refusal_identifies_the_operation_even_without_subjects() {
    for (operation, role, position) in [
        ("organizer-products", "mechanic", "before"),
        ("organizer-practice", "intent", "after"),
    ] {
        let loaded = load(&source(operation, role, position)).expect("the fixture artifact loads");
        let mut graph = MemoryGraph::new();
        let resolver = StableElementResolver::seal(
            &graph,
            "organizer/fixture",
            &HashMap::new(),
            &HashMap::new(),
        )
        .expect("the fixture seals the prepared period");
        let mut sink = CollectingSink::default();
        let error = tick::run_tick(
            &loaded,
            &TypeEnv {
                fields: HashMap::new(),
                exemptions: &[],
            },
            &EnumRegistry::default(),
            &EmptyIntrinsicHost,
            &mut graph,
            &mut sink,
            &IntrinsicCosts::default(),
            &DefinesEnv::new(),
            1,
            RngSeedContext {
                session: &ReplaySessionId::try_from("organizer-host-refusal")
                    .expect("the fixture value fits the target range"),
                seed: ReplaySeed::new(0),
            },
            &resolver,
            Some(&ClosedVocabulary::default()),
        )
        .expect_err("the fixture run completes");
        assert!(
            error
                .message
                .contains(&format!("graph evaluator cannot execute {operation}")),
            "refusal must identify the unsupported invocation: {error}"
        );
        assert!(error.message.contains("material runtime host"));
        assert!(sink.events.is_empty());
    }
}

#[test]
fn organizer_native_bodies_are_not_certified_by_a_graph_only_synthetic_audit() {
    for (operation, role, position) in [
        ("organizer-products", "mechanic", "before"),
        ("organizer-practice", "intent", "after"),
    ] {
        let loaded = load(&source(operation, role, position)).expect("the fixture artifact loads");
        assert_eq!(
            babylon_bsl::sfs_profile::audit_rule_footprint(
                &loaded.rule,
                &babylon_bsl::vocabulary::ClosedVocabulary::default(),
                &CardinalityCeilings::new(HashMap::new(), HashMap::new()),
                &IntrinsicCosts::default(),
                &[],
            )
            .expect_err("the fixture call `audit_rule_footprint` fails for the authored inputs"),
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
