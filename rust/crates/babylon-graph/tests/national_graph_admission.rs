//! The measured aggregate national opening uses 129,865 stable nodes.
use std::collections::HashMap;

use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::{StableElementResolver, StableIdentityError};
use babylon_graph::stable_state::{
    compose_stable_graph_state_from_rows, StableGraphStateRowsInput,
};
use babylon_graph::substrate::GraphSubstrate;

fn rows(count: usize) -> StableGraphStateRowsInput {
    StableGraphStateRowsInput {
        nodes: (0..count)
            .map(|index| (format!("workplace-{index:06}"), "BUSINESS".to_owned()))
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
    let admitted = compose_stable_graph_state_from_rows("national-world", rows(129_865)).unwrap();
    assert_eq!(admitted.rows().nodes().len(), 129_865);
    assert!(compose_stable_graph_state_from_rows("national-world", rows(131_073)).is_err());
}

#[test]
fn resolver_admission_covers_the_same_nodes_and_retains_a_finite_ceiling() {
    let mut graph = HypergraphStore::new();
    let mut names = HashMap::new();
    for index in 0..129_865 {
        let node = graph.add_node("BUSINESS").unwrap();
        names.insert(node, format!("workplace-{index:06}"));
    }
    let admitted = StableElementResolver::seal(&graph, "national-world", &names, &HashMap::new());
    assert!(admitted.is_ok(), "{admitted:?}");
    for index in 129_865..131_073 {
        let node = graph.add_node("BUSINESS").unwrap();
        names.insert(node, format!("workplace-{index:06}"));
    }
    assert!(matches!(
        StableElementResolver::seal(&graph, "national-world", &names, &HashMap::new()),
        Err(StableIdentityError::ResolverRowLimit {
            actual: 131_073,
            maximum: 131_072
        })
    ));
}
