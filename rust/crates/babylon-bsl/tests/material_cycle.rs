//! The authored native invocation is closed and cannot silently become a graph rule.

use babylon_bsl::bindings::BindingVocabulary;
use babylon_bsl::causal_contract::{
    authorize_rule_effects, effect_footprint, parse_rule_contract, ContractError, EffectSignature,
};
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::EmptyIntrinsicHost;
use babylon_bsl::rule_pipeline::{load_rule, LoadContext, LoadError, LoadedRule, RuleExecution};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::{run_tick, DefinesEnv};
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::EnumRegistry;
use babylon_bsl::vocabulary::{ClosedVocabulary, EnumKind};
use babylon_graph::memory::MemoryGraph;
use babylon_graph::stable_element::StableElementResolver;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId, RngSeedContext};
use std::collections::{HashMap, HashSet};

const RULE: &str = r#"(rule material/period
  :role mechanic :evidence designed
  :material-basis "Invokes the current material period once after metabolism."
  :fuel 1000000
  (anchor :after metabolism)
  (material-cycle))"#;

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
            systems: &HashSet::from(["metabolism".to_owned(), "vitality".to_owned()]),
            vocabulary_registry: Some(
                &ClosedVocabulary::new([(EnumKind::EventType, vec!["PROBE".to_owned()])]).unwrap(),
            ),
            rule_file: "material/period.bsl",
        },
    )
}

#[test]
fn material_cycle_loads_without_graph_bindings_or_domain_and_charges_full_invocation() {
    let loaded = load(RULE).expect("the closed native rule must load");
    assert_eq!(loaded.execution, RuleExecution::MaterialCycle);
    assert!(loaded.bindings.is_empty());
    assert!(loaded.domain.is_none());
    assert_eq!(loaded.static_bound, 1_000_000);
    assert_eq!(loaded.declared_fuel, 1_000_000);
    assert!(loaded.kernel.is_none());
    assert!(loaded.projection.is_none());
    assert!(load(&RULE.replace("material/period", "campaign/custom-period")).is_ok());
}

#[test]
fn material_cycle_rejects_partial_fuel_instead_of_discounting_the_native_operation() {
    let error = load(&RULE.replace(":fuel 1000000", ":fuel 999999")).unwrap_err();
    assert_eq!(error.spec_code(), Some("E-LOAD-040"));
}

#[test]
fn material_cycle_rejects_any_extra_body_or_nested_invocation() {
    for replacement in [
        "(bindings) (material-cycle)",
        "(domain :graph) (material-cycle)",
        "(when #t) (material-cycle)",
        "(effects (emit EventType/PROBE)) (material-cycle)",
        "(material-cycle) (material-cycle)",
        "(material-cycle 1)",
        "(material-cycle :as cycle)",
        "(material-cycle (material-cycle))",
        "(effects (material-cycle))",
        "(effects (guard #t (material-cycle)))",
        "(bindings (binding cycle :expr (material-cycle))) (effects (emit EventType/PROBE))",
        "(unknown (material-cycle))",
    ] {
        let source = RULE.replace("(material-cycle)", replacement);
        assert!(
            matches!(load(&source), Err(LoadError::Surface(_))),
            "wrong refusal for {replacement}"
        );
    }
}

#[test]
fn material_cycle_has_an_explicit_mechanic_only_effect_footprint() {
    let (rule, _) = babylon_bsl::reader::read(RULE).unwrap();
    assert_eq!(
        effect_footprint(&rule).unwrap(),
        [EffectSignature::MaterialCycle]
    );
    let contract = parse_rule_contract(&rule).unwrap();
    assert!(authorize_rule_effects(&rule, &contract).is_ok());
    for role in ["recognizer", "external-event", "intent"] {
        let source = RULE
            .replace("material/period", "campaign/custom-period")
            .replace(":role mechanic", &format!(":role {role}"));
        let error = load(&source).unwrap_err();
        assert!(
            matches!(
                error,
                LoadError::Causal(ContractError::UnauthorizedEffect {
                    effect: EffectSignature::MaterialCycle,
                    ..
                })
            ),
            "{role}: {error}"
        );
    }
}

#[test]
fn material_cycle_cannot_escape_to_intrinsic_expression_dispatch() {
    let (expression, _) = babylon_bsl::reader::read("(material-cycle)").unwrap();
    let mut fuel = 1_000_000;
    let error = babylon_bsl::evaluator::evaluate(
        &expression,
        &babylon_bsl::evaluator::EvalEnv {
            bindings: HashMap::new(),
            intrinsic_costs: &IntrinsicCosts::default(),
            graph: None,
            types: None,
            enums: None,
            elements: Vec::new(),
            draw_context: None,
        },
        &EmptyIntrinsicHost,
        &mut fuel,
    )
    .unwrap_err();
    assert!(error.message.contains("material runtime host"), "{error}");
    assert_eq!(fuel, 1_000_000);
}

#[test]
fn material_cycle_payload_label_is_data_but_payload_value_invocations_are_refused() {
    let source = r#"(rule campaign/label
      :role mechanic :evidence designed :material-basis "Event payload labels carry data."
      :fuel 100 (anchor :after metabolism) (domain :graph) (bindings)
      (effects (emit EventType/PROBE (material-cycle 7))))"#;
    let loaded = load(source).expect("a payload label is not an invocation");
    assert_eq!(loaded.execution, RuleExecution::Graph);
    assert_eq!(loaded.static_bound, 3);
    assert_eq!(
        effect_footprint(&loaded.rule).unwrap(),
        [EffectSignature::Event("EventType/PROBE".to_owned())]
    );
    for payload in [
        "(material-cycle (material-cycle))",
        "(value (material-cycle))",
        "(value 7 (material-cycle))",
        "(value (emit (material-cycle)))",
    ] {
        assert!(
            matches!(
                load(&source.replace("(material-cycle 7)", payload)),
                Err(LoadError::Surface(_))
            ),
            "missed {payload}"
        );
    }
}

#[test]
fn material_cycle_synthetic_audit_explicitly_refuses_uninspected_native_body() {
    let loaded = load(RULE).unwrap();
    assert_eq!(
        babylon_bsl::sfs_profile::audit_rule_footprint(
            &loaded.rule,
            &ClosedVocabulary::default(),
            &CardinalityCeilings::new(HashMap::new(), HashMap::new()),
            &IntrinsicCosts::default(),
            &[],
        )
        .unwrap_err(),
        babylon_bsl::sfs_profile::SfsProfileError::NativeMaterialCycleUnsupported
    );
}

#[test]
fn material_cycle_requires_designed_mechanic_and_exact_anchor() {
    for (from, to) in [
        (":role mechanic", ":role recognizer"),
        (":role mechanic", ":role external-event"),
        (":role mechanic", ":role intent"),
        (":evidence designed", ":evidence derived"),
        (":evidence designed", ":evidence observed"),
        (":evidence designed", ":evidence calibrated"),
        ("(anchor :after metabolism)", ""),
        ("(anchor :after metabolism)", "(anchor :before metabolism)"),
        ("(anchor :after metabolism)", "(anchor :after vitality)"),
        (
            "(anchor :after metabolism)",
            "(anchor :after metabolism) (anchor :after metabolism)",
        ),
        (":fuel 1000000", ":fuel 1000000 :unknown #t"),
        (":fuel 1000000", ":fuel 1000000 :fuel 1000000"),
    ] {
        assert!(
            load(&RULE.replace(from, to)).is_err(),
            "unexpectedly accepted {to}"
        );
    }
}

#[test]
fn material_cycle_graph_evaluator_refuses_without_host_even_with_zero_subjects() {
    let loaded = load(RULE).expect("the closed native rule must load");
    let mut graph = MemoryGraph::new();
    let resolver =
        StableElementResolver::seal(&graph, "material/fixture", &HashMap::new(), &HashMap::new())
            .unwrap();
    let mut sink = CollectingSink::default();
    let error = run_tick(
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
            session: &ReplaySessionId::try_from("material-cycle-loading").unwrap(),
            seed: ReplaySeed::new(0),
        },
        &resolver,
        Some(&ClosedVocabulary::default()),
    )
    .unwrap_err();
    assert!(error.message.contains("material runtime host"), "{error}");
    assert!(sink.events.is_empty());
}
