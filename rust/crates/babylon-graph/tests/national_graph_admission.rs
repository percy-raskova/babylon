//! Row admission covers the measured 179,772-node household opening.
//! Compact fixture names isolate row limits from the independent byte ceiling.
use std::collections::HashMap;

use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::{StableElementKey, StableElementResolver, StableIdentityError};
use babylon_graph::stable_state::{
    compose_stable_graph_state_from_rows, StableGraphStateRowsInput,
};
use babylon_graph::substrate::GraphSubstrate;

const MEASURED_NODES: usize = 179_772;
const NODE_CEILING: usize = 262_144;

fn local_name(index: usize) -> String {
    format!("n{index:06}")
}

fn rows(count: usize) -> StableGraphStateRowsInput {
    StableGraphStateRowsInput {
        nodes: (0..count)
            .map(|index| (local_name(index), "BUSINESS".to_owned()))
            .collect(),
        node_f64: vec![],
        edges: vec![],
        hyperedges: vec![],
        edge_f64: vec![],
        node_currency: vec![],
        hyperedge_f64: vec![],
    }
}

#[test]
fn canonical_node_admission_covers_the_measured_aggregate_opening() {
    for count in [MEASURED_NODES, NODE_CEILING] {
        let admitted = compose_stable_graph_state_from_rows("national-world", rows(count)).unwrap();
        assert_eq!(admitted.rows().nodes().len(), count);
        assert_eq!(
            admitted.rows().nodes().last(),
            Some(&(local_name(count - 1), "BUSINESS".to_owned()))
        );
        let mut duplicate = rows(count);
        duplicate.nodes[count - 1].0 = local_name(0);
        assert!(matches!(
            compose_stable_graph_state_from_rows("national-world", duplicate),
            Err(StableIdentityError::DuplicateFact { section: "nodes" })
        ));
    }
    assert!(matches!(
        compose_stable_graph_state_from_rows("national-world", rows(NODE_CEILING + 1)),
        Err(StableIdentityError::StateSectionLimit {
            section: "nodes",
            actual: 262_145,
            maximum: NODE_CEILING,
        })
    ));
}

#[test]
fn resolver_admission_covers_the_same_nodes_and_retains_a_finite_ceiling() {
    let mut graph = HypergraphStore::new();
    let mut names = HashMap::new();
    for index in 0..=NODE_CEILING {
        let node = graph.add_node("BUSINESS").unwrap();
        names.insert(node, local_name(index));
        let count = index + 1;
        if [MEASURED_NODES, NODE_CEILING].contains(&count) {
            let admitted =
                StableElementResolver::seal(&graph, "national-world", &names, &HashMap::new())
                    .unwrap();
            assert_eq!(
                admitted.node_key(node).unwrap(),
                &StableElementKey::Node {
                    scenario: "national-world".to_owned(),
                    local_name: local_name(index),
                }
            );
            names.insert(node, local_name(0));
            assert!(matches!(
                StableElementResolver::seal(&graph, "national-world", &names, &HashMap::new()),
                Err(StableIdentityError::DuplicateNodeName { .. })
            ));
            names.insert(node, local_name(index));
        }
    }
    assert!(matches!(
        StableElementResolver::seal(&graph, "national-world", &names, &HashMap::new()),
        Err(StableIdentityError::ResolverRowLimit {
            actual: 262_145,
            maximum: NODE_CEILING,
        })
    ));
}

#[test]
fn resolver_manifest_admits_exact_sixteen_mib_and_rejects_plus_one() {
    const MAXIMUM: usize = 16_777_216;
    for final_type_bytes in [92, 93] {
        let mut graph = HypergraphStore::new();
        let mut names = HashMap::new();
        for index in 0..83_885 {
            let node = graph.add_node(&"T".repeat(128)).unwrap();
            names.insert(node, format!("n{index:063}"));
        }
        let final_node = graph.add_node(&"T".repeat(final_type_bytes)).unwrap();
        let final_name = format!("z{:063}", 83_885);
        names.insert(final_node, final_name.clone());
        let result = StableElementResolver::seal(&graph, "s", &names, &HashMap::new());
        if final_type_bytes == 93 {
            assert!(matches!(
                result,
                Err(StableIdentityError::ByteLimit {
                    field: "stable element resolver manifest",
                    actual: 16_777_217,
                    maximum: MAXIMUM,
                })
            ));
            continue;
        }
        let admitted = result.unwrap();
        assert_eq!(
            admitted.node_key(final_node).unwrap(),
            &StableElementKey::Node {
                scenario: "s".to_owned(),
                local_name: final_name,
            }
        );
        let bytes = admitted.manifest().canonical_bytes();
        assert_eq!(bytes.len(), MAXIMUM);
        assert_eq!(&bytes[MAXIMUM - 97..MAXIMUM - 5], "T".repeat(92).as_bytes());
        assert_eq!(&bytes[MAXIMUM - 5..], &[3, 0, 0, 0, 0]);
    }
}
