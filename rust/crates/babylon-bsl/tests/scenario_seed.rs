//! Captured typed instances share the authored scenario admission semantics.
use babylon_bsl::reader::{ScaledKind, ScaledLit};
use babylon_bsl::scenario::{load_scenario, LoadedScenario};
use babylon_bsl::scenario_seed::{
    load_scenario_with_seed, EdgeSeed, GraphSeed, HyperedgeSeed, NodeSeed, SeedAttribute, SeedValue,
};
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::StableElementResolver;
use babylon_graph::stable_state::encode_stable_graph_state;
use babylon_kernel::currency::Currency;

const DECLARATIONS: &str = r"
(scenario capture/control
 (defvocabulary NodeType (SOCIAL_CLASS))
 (defvocabulary EdgeType (SOLIDARITY))
 (defvocabulary HyperedgeType (ECONOMIC_SECTOR))
 (deffield social-class/employed-population int extensive)
 (deffield social-class/reserve-population int extensive)
 (deffield social-class/cash currency extensive))";

fn node(name: &str, employed: i64) -> NodeSeed {
    NodeSeed {
        local_name: name.to_owned(),
        node_type: "SOCIAL_CLASS".to_owned(),
        attributes: vec![
            SeedAttribute {
                field: "social-class/employed-population".to_owned(),
                value: SeedValue::Integer(employed),
            },
            SeedAttribute {
                field: "social-class/reserve-population".to_owned(),
                value: SeedValue::Integer(2),
            },
            SeedAttribute {
                field: "social-class/cash".to_owned(),
                value: SeedValue::Currency(Currency::from_micro_units(3_000_001)),
            },
        ],
    }
}

fn graph_bytes(graph: &HypergraphStore, loaded: &LoadedScenario) -> Vec<u8> {
    let resolver = StableElementResolver::seal(
        graph,
        &loaded.id,
        &loaded.node_content_ids,
        &loaded.hyperedge_content_ids,
    )
    .unwrap();
    encode_stable_graph_state(graph, &resolver)
        .unwrap()
        .canonical_bytes()
        .to_vec()
}

#[test]
fn typed_nodes_edges_and_native_membership_equal_authored_instances() {
    let seed = GraphSeed::try_new(
        vec![node("workers-b", 8), node("workers-a", 4)],
        vec![EdgeSeed {
            edge_type: "SOLIDARITY".to_owned(),
            source: "workers-a".to_owned(),
            target: "workers-b".to_owned(),
            strength: SeedValue::Scaled(ScaledLit {
                kind: ScaledKind::Coefficient,
                unscaled: 5,
                scale: 1,
            }),
            attributes: vec![],
        }],
        vec![HyperedgeSeed {
            local_name: "sector".to_owned(),
            hyperedge_type: "ECONOMIC_SECTOR".to_owned(),
            members: vec!["workers-a".to_owned(), "workers-b".to_owned()],
            attributes: vec![],
        }],
    )
    .unwrap();
    let mut typed = HypergraphStore::new();
    let loaded = load_scenario_with_seed(DECLARATIONS, None, &seed, &mut typed).unwrap();
    let authored = DECLARATIONS.strip_suffix(')').unwrap().to_owned()
        + r"
 (node workers-a NodeType/SOCIAL_CLASS
  (social-class/employed-population 4) (social-class/reserve-population 2)
  (social-class/cash 3.000001$))
 (node workers-b NodeType/SOCIAL_CLASS
  (social-class/employed-population 8) (social-class/reserve-population 2)
  (social-class/cash 3.000001$))
 (edge EdgeType/SOLIDARITY workers-a workers-b 0.5c)
 (hyperedge sector HyperedgeType/ECONOMIC_SECTOR (members workers-a workers-b)))";
    let mut text = HypergraphStore::new();
    let authored = load_scenario(&authored, &mut text).unwrap();
    assert_eq!(graph_bytes(&typed, &loaded), graph_bytes(&text, &authored));
    assert_eq!(loaded.node_count, 2);
    assert_eq!(loaded.edge_count, 1);
    assert_eq!(loaded.hyperedge_types["ECONOMIC_SECTOR"], 1);
    assert_eq!(loaded.max_members_seen["ECONOMIC_SECTOR"], 2);
}

#[test]
fn captured_seed_refuses_duplicate_authority_and_invalid_literal_domains() {
    assert!(
        GraphSeed::try_new(vec![node("workers", 1), node("workers", 2)], vec![], vec![]).is_err()
    );
    let mut duplicate = node("workers", 1);
    duplicate.attributes.push(duplicate.attributes[0].clone());
    assert!(GraphSeed::try_new(vec![duplicate], vec![], vec![]).is_err());
    for invalid in [
        SeedValue::Integer(9_007_199_254_740_993),
        SeedValue::Currency(Currency::from_micro_units(-1)),
        SeedValue::Scaled(ScaledLit {
            kind: ScaledKind::Coefficient,
            unscaled: 11,
            scale: 1,
        }),
        SeedValue::Scaled(ScaledLit {
            kind: ScaledKind::Coefficient,
            unscaled: 5,
            scale: 10,
        }),
    ] {
        let mut row = node("workers", 1);
        row.attributes[0].value = invalid;
        assert!(GraphSeed::try_new(vec![row], vec![], vec![]).is_err());
    }
}

#[test]
fn seed_admission_requires_declared_fields_closed_types_and_known_endpoints() {
    let mut unknown_field = node("workers", 1);
    unknown_field.attributes[0].field = "social-class/undeclared".to_owned();
    let mut unknown_type = node("workers", 1);
    unknown_type.node_type = "INVENTED_CLASS".to_owned();
    for row in [unknown_field, unknown_type] {
        let seed = GraphSeed::try_new(vec![row], vec![], vec![]).unwrap();
        assert!(
            load_scenario_with_seed(DECLARATIONS, None, &seed, &mut HypergraphStore::new())
                .is_err()
        );
    }
    assert!(GraphSeed::try_new(
        vec![node("workers", 1)],
        vec![EdgeSeed {
            edge_type: "SOLIDARITY".to_owned(),
            source: "workers".to_owned(),
            target: "absent".to_owned(),
            strength: SeedValue::Integer(1),
            attributes: vec![],
        }],
        vec![]
    )
    .is_err());
    let seed = GraphSeed::try_new(vec![node("workers", 1)], vec![], vec![]).unwrap();
    assert!(load_scenario_with_seed(
        "(scenario capture/control (node hidden NodeType/SOCIAL_CLASS))",
        None,
        &seed,
        &mut HypergraphStore::new(),
    )
    .is_err());
}

#[test]
fn native_seed_preserves_practice_topology_admission() {
    let declarations = "(scenario capture/practice
      (defvocabulary NodeType (ORGANIZATION))
      (deffield organization/active int intensive)
      (deffield organization/action-budget int intensive))";
    let seed = GraphSeed::try_new(
        vec![NodeSeed {
            local_name: "organization".to_owned(),
            node_type: "ORGANIZATION".to_owned(),
            attributes: vec![SeedAttribute {
                field: "organization/active".to_owned(),
                value: SeedValue::Integer(1),
            }],
        }],
        vec![],
        vec![],
    )
    .unwrap();
    let error = load_scenario_with_seed(declarations, None, &seed, &mut HypergraphStore::new())
        .unwrap_err();
    assert_eq!(error.code, Some("E-LOAD-063"));
}
