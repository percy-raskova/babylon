//! `deffield ... :member` in the scenario dialect (Amendment AG clause i, §2.9): the declaration
//! lands in `LoadedScenario::membership_fields`, and the refusals carry their codes. The rule
//! dialect's twins live in `declarations.rs`; the wrong-form law (`E-LOAD-046`) in `grammar.rs`.

use babylon_bsl::declarations::FieldRegistry;
use babylon_bsl::reader;
use babylon_bsl::scenario;
use babylon_bsl::types::EnumRegistry;
use babylon_bsl::types::{BslType, FieldKind};
use babylon_bsl::vocabulary::{ClosedVocabulary, EnumKind};
use babylon_graph::memory::MemoryGraph;

#[test]
fn deffield_member_declares_a_membership_field() {
    let mut graph = MemoryGraph::new();
    let loaded = scenario::load_scenario(
        r"
(scenario ft/membership-fields
  (defvocabulary NodeType (SOCIAL_CLASS))
  (defvocabulary HyperedgeType (NATION))
  (defenum Tier (LOW HIGH))
  (deffield nation/households int extensive :member NodeType/SOCIAL_CLASS)
  (deffield nation/tier enum Tier :member NodeType/SOCIAL_CLASS)
  (deffield nation/count int extensive))
",
        &mut graph,
    )
    .expect("membership fields declare in the scenario dialect");
    assert_eq!(loaded.membership_fields.len(), 2);
    assert_eq!(
        loaded.membership_fields.get("nation/households"),
        Some(&"SOCIAL_CLASS".to_owned())
    );
    assert_eq!(
        loaded.membership_fields.get("nation/tier"),
        Some(&"SOCIAL_CLASS".to_owned())
    );
    // One namespace: the type and kind live in `fields`, and a plain
    // field of the same owner is not marked.
    assert_eq!(loaded.fields["nation/households"].ty, BslType::Int);
    assert_eq!(
        loaded.fields["nation/households"].kind,
        FieldKind::Extensive
    );
    assert!(matches!(loaded.fields["nation/tier"].ty, BslType::Enum(_)));
    assert!(loaded.fields.contains_key("nation/count"));
    assert!(!loaded.membership_fields.contains_key("nation/count"));
}

#[test]
fn member_on_a_node_owner_is_e_load_048() {
    for owner in ["social-class/households", "solidarity/households"] {
        let mut graph = MemoryGraph::new();
        let source = format!(
            "(scenario ft/m (defvocabulary NodeType (SOCIAL_CLASS)) \
             (defvocabulary EdgeType (SOLIDARITY)) \
             (defvocabulary HyperedgeType (NATION)) \
             (deffield {owner} int extensive :member NodeType/SOCIAL_CLASS))"
        );
        let err = scenario::load_scenario(&source, &mut graph)
            .expect_err("a node or edge owner carries no membership");
        assert_eq!(err.code, Some("E-LOAD-048"), "{owner}: {}", err.message);
    }
    // An owner that renders nothing registered is E-LOAD-023, as for any field.
    let mut graph = MemoryGraph::new();
    let err = scenario::load_scenario(
        "(scenario ft/m (defvocabulary NodeType (SOCIAL_CLASS)) \
         (defvocabulary HyperedgeType (NATION)) \
         (deffield nowhere/households int extensive :member NodeType/SOCIAL_CLASS))",
        &mut graph,
    )
    .expect_err("the owner renders nothing registered");
    assert_eq!(err.code, Some("E-LOAD-023"), "{}", err.message);
}

#[test]
fn member_naming_an_edge_type_is_e_type_011() {
    let mut graph = MemoryGraph::new();
    let err = scenario::load_scenario(
        "(scenario ft/m (defvocabulary NodeType (SOCIAL_CLASS)) \
         (defvocabulary EdgeType (SOLIDARITY)) \
         (defvocabulary HyperedgeType (NATION)) \
         (deffield nation/households int extensive :member EdgeType/SOLIDARITY))",
        &mut graph,
    )
    .expect_err("the member half is a NodeType");
    assert_eq!(err.code, Some("E-TYPE-011"), "{}", err.message);
    // The operand's KIND is positional: it needs no vocabulary at all.
    let mut graph = MemoryGraph::new();
    let err = scenario::load_scenario(
        "(scenario ft/m (deffield nation/households int extensive :member EdgeType/SOLIDARITY))",
        &mut graph,
    )
    .expect_err("the member half is a NodeType");
    assert_eq!(err.code, Some("E-TYPE-011"), "{}", err.message);
    // An unregistered NodeType member is the vocabulary's refusal.
    let mut graph = MemoryGraph::new();
    let err = scenario::load_scenario(
        "(scenario ft/m (defvocabulary NodeType (SOCIAL_CLASS)) \
         (defvocabulary HyperedgeType (NATION)) \
         (deffield nation/households int extensive :member NodeType/NOBODY))",
        &mut graph,
    )
    .expect_err("the member is not registered");
    assert_eq!(err.code, Some("E-LOAD-031"), "{}", err.message);
}

#[test]
fn a_currency_membership_field_is_refused() {
    let mut graph = MemoryGraph::new();
    let err = scenario::load_scenario(
        "(scenario ft/m (defvocabulary NodeType (SOCIAL_CLASS)) \
         (defvocabulary HyperedgeType (NATION)) \
         (deffield nation/stake currency extensive :member NodeType/SOCIAL_CLASS))",
        &mut graph,
    )
    .expect_err("there is no Currency lane off nodes");
    assert!(
        err.message.contains("no edge-scoped Currency lane"),
        "{}",
        err.message
    );
}

#[test]
fn a_declaration_wrong_in_owner_and_operand_gets_the_same_code_in_both_dialects() {
    // §2.9 checks the owner first: a node owner (E-LOAD-048) wins over an edge-type operand
    // (E-TYPE-011), in the scenario dialect as in the rule dialect.
    let mut graph = MemoryGraph::new();
    let err = scenario::load_scenario(
        "(scenario ft/m (defvocabulary NodeType (SOCIAL_CLASS)) \
         (defvocabulary EdgeType (SOLIDARITY)) \
         (defvocabulary HyperedgeType (NATION)) \
         (deffield social-class/households int extensive :member EdgeType/SOLIDARITY))",
        &mut graph,
    )
    .expect_err("the declaration is wrong in both ways");
    assert_eq!(err.code, Some("E-LOAD-048"), "{}", err.message);

    let vocabulary = ClosedVocabulary::new([
        (EnumKind::NodeType, vec!["SOCIAL_CLASS".to_owned()]),
        (EnumKind::EdgeType, vec!["SOLIDARITY".to_owned()]),
        (EnumKind::HyperedgeType, vec!["NATION".to_owned()]),
    ])
    .expect("the fixture vocabulary is disjoint");
    let mut registry = FieldRegistry::default();
    let rule_err = registry
        .declare(
            &reader::read(
                "(deffield social-class/households :type int :kind extensive \
                 :member EdgeType/SOLIDARITY)",
            )
            .expect("parses")
            .0,
            &vocabulary,
            &EnumRegistry::default(),
        )
        .expect_err("the declaration is wrong in both ways");
    assert_eq!(rule_err.spec_code(), err.code);
}
