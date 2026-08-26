use std::collections::HashMap;

use babylon_graph::memory::MemoryGraph;
use babylon_graph::stable_element::{
    StableElementKeyV1, StableElementResolverV1, StableIdentityError,
    MAX_STABLE_CARRIER_ACTIVE_ELEMENTS_V2, MAX_STABLE_CARRIER_BYTES_V2,
    MAX_STABLE_RESOLVER_MANIFEST_BYTES_V1, MAX_STABLE_RESOLVER_ROWS_V1,
};
use babylon_graph::substrate::{GraphSubstrate, HyperedgeId, NodeId};

struct StableFixture {
    graph: MemoryGraph,
    owners: NodeId,
    workers: NodeId,
    coalition_a: HyperedgeId,
    coalition_b: HyperedgeId,
    node_names: HashMap<NodeId, String>,
    hyperedge_names: HashMap<HyperedgeId, String>,
}

fn fixture() -> StableFixture {
    let mut graph = MemoryGraph::new();
    let owners = graph.add_node("class").unwrap();
    let workers = graph.add_node("class").unwrap();
    graph.add_edge("solidarity", workers, owners, 0.75).unwrap();
    let coalition_a = graph
        .add_hyperedge("coalition", &[workers, owners])
        .unwrap();
    let coalition_b = graph
        .add_hyperedge("coalition", &[owners, workers])
        .unwrap();
    let node_names = HashMap::from([
        (workers, "workers".to_owned()),
        (owners, "owners".to_owned()),
    ]);
    let hyperedge_names = HashMap::from([
        (coalition_b, "coalition-b".to_owned()),
        (coalition_a, "coalition-a".to_owned()),
    ]);
    StableFixture {
        graph,
        owners,
        workers,
        coalition_a,
        coalition_b,
        node_names,
        hyperedge_names,
    }
}

fn resolver(value: &StableFixture) -> StableElementResolverV1 {
    StableElementResolverV1::seal(
        &value.graph,
        "demo/world",
        &value.node_names,
        &value.hyperedge_names,
    )
    .unwrap()
}

fn str32(value: &str) -> Vec<u8> {
    let mut output = Vec::new();
    output.extend_from_slice(&u32::try_from(value.len()).unwrap().to_be_bytes());
    output.extend_from_slice(value.as_bytes());
    output
}

#[test]
fn stable_element_binary_keys_and_ascii_segments_are_exact() {
    let value = fixture();
    let resolver = resolver(&value);
    let node = resolver.node_key(value.workers).unwrap();
    let edge = resolver
        .edge_key("solidarity", value.workers, value.owners)
        .unwrap();
    let hyperedge = resolver.hyperedge_key(value.coalition_a).unwrap();

    let expected_node = [
        b"babylon.stable-element\0".as_slice(),
        &1_u32.to_be_bytes(),
        &[0x01],
        &str32("demo/world"),
        &str32("workers"),
    ]
    .concat();
    let expected_edge = [
        b"babylon.stable-element\0".as_slice(),
        &1_u32.to_be_bytes(),
        &[0x02],
        &str32("demo/world"),
        &str32("solidarity"),
        &str32("workers"),
        &str32("owners"),
    ]
    .concat();
    let expected_hyperedge = [
        b"babylon.stable-element\0".as_slice(),
        &1_u32.to_be_bytes(),
        &[0x03],
        &str32("demo/world"),
        &str32("coalition-a"),
    ]
    .concat();

    assert_eq!(node.canonical_bytes().unwrap(), expected_node);
    assert_eq!(edge.canonical_bytes().unwrap(), expected_edge);
    assert_eq!(hyperedge.canonical_bytes().unwrap(), expected_hyperedge);
    assert_eq!(
        node.carrier_segment().unwrap().as_str(),
        "4:node|10:demo/world|7:workers"
    );
    assert_eq!(
        edge.carrier_segment().unwrap().as_str(),
        "4:edge|10:demo/world|10:solidarity|7:workers|6:owners"
    );
    assert_eq!(
        hyperedge.carrier_segment().unwrap().as_str(),
        "9:hyperedge|10:demo/world|11:coalition-a"
    );
}

#[test]
fn carrier_reframes_resolved_elements_in_outermost_to_innermost_order() {
    let value = fixture();
    let resolver = resolver(&value);
    let subject = resolver.node_key(value.workers).unwrap().clone();
    let edge = resolver
        .edge_key("solidarity", value.workers, value.owners)
        .unwrap();
    let hyperedge = resolver.hyperedge_key(value.coalition_a).unwrap().clone();
    let mixed = resolver
        .carrier_key(&subject, &[edge, hyperedge], -7)
        .unwrap();
    assert_eq!(
        mixed.validated_bytes(),
        b"30:4:node|10:demo/world|7:workers|53:4:edge|10:demo/world|10:solidarity|7:workers|6:owners|40:9:hyperedge|10:demo/world|11:coalition-a|2:-7"
    );

    let zero_active = resolver.carrier_key(&subject, &[], 0).unwrap();
    assert_eq!(
        zero_active.validated_bytes(),
        b"30:4:node|10:demo/world|7:workers|1:0"
    );
    let minimum_slot = resolver.carrier_key(&subject, &[], i64::MIN).unwrap();
    assert!(minimum_slot
        .validated_bytes()
        .ends_with(b"|20:-9223372036854775808"));
}

#[test]
fn carrier_accepts_256_active_elements_and_refuses_257_before_allocation() {
    let value = fixture();
    let resolver = resolver(&value);
    let subject = resolver.node_key(value.workers).unwrap().clone();
    let active = vec![subject.clone(); MAX_STABLE_CARRIER_ACTIVE_ELEMENTS_V2];
    let maximum = resolver.carrier_key(&subject, &active, i64::MAX).unwrap();
    assert!(maximum.validated_bytes().len() <= MAX_STABLE_CARRIER_BYTES_V2);

    let too_many = vec![subject.clone(); MAX_STABLE_CARRIER_ACTIVE_ELEMENTS_V2 + 1];
    assert_eq!(
        resolver.carrier_key(&subject, &too_many, 0),
        Err(StableIdentityError::ActiveElementLimit {
            actual: MAX_STABLE_CARRIER_ACTIVE_ELEMENTS_V2 + 1,
            maximum: MAX_STABLE_CARRIER_ACTIVE_ELEMENTS_V2,
        })
    );
}

#[test]
fn resolver_manifest_is_exact_sorted_and_parallel_hyperedges_stay_distinct() {
    let value = fixture();
    let resolver = resolver(&value);
    let expected = [
        b"babylon.stable-element-resolver\0".as_slice(),
        &1_u32.to_be_bytes(),
        &[0x01],
        &str32("demo/world"),
        &[0x02],
        &2_u32.to_be_bytes(),
        &str32("owners"),
        &str32("class"),
        &str32("workers"),
        &str32("class"),
        &[0x03],
        &2_u32.to_be_bytes(),
        &str32("coalition-a"),
        &str32("coalition"),
        &str32("coalition-b"),
        &str32("coalition"),
    ]
    .concat();

    assert_eq!(resolver.manifest().canonical_bytes(), expected);
    assert_eq!(
        resolver.manifest().digest(),
        [
            0x93, 0xbe, 0xce, 0x63, 0xe9, 0x36, 0xcb, 0x85, 0xa9, 0x85, 0xed, 0x5e, 0xfa, 0x4f,
            0xe7, 0x94, 0x5d, 0x94, 0x60, 0xba, 0x92, 0xf9, 0xbe, 0x2c, 0x87, 0x31, 0x98, 0x11,
            0xa4, 0x39, 0xf6, 0x11,
        ]
    );
    assert_ne!(
        resolver.hyperedge_key(value.coalition_a).unwrap(),
        resolver.hyperedge_key(value.coalition_b).unwrap()
    );
    assert!(resolver.manifest().canonical_bytes().len() <= MAX_STABLE_RESOLVER_MANIFEST_BYTES_V1);
}

#[test]
fn resolver_seal_requires_exact_bijections_and_strict_ascii_names() {
    let value = fixture();
    let mut missing = value.node_names.clone();
    missing.remove(&value.workers);
    assert_eq!(
        StableElementResolverV1::seal(&value.graph, "demo/world", &missing, &value.hyperedge_names,),
        Err(StableIdentityError::MissingNodeName {
            node: value.workers,
        })
    );

    let mut duplicate = value.node_names.clone();
    duplicate.insert(value.workers, "owners".to_owned());
    assert_eq!(
        StableElementResolverV1::seal(
            &value.graph,
            "demo/world",
            &duplicate,
            &value.hyperedge_names,
        ),
        Err(StableIdentityError::DuplicateNodeName {
            local_name: "owners".to_owned(),
        })
    );

    let mut extra = value.node_names.clone();
    extra.insert(NodeId(999), "ghost".to_owned());
    assert_eq!(
        StableElementResolverV1::seal(&value.graph, "demo/world", &extra, &value.hyperedge_names,),
        Err(StableIdentityError::ExtraNodeName { node: NodeId(999) })
    );

    let mut non_ascii = value.node_names.clone();
    non_ascii.insert(value.workers, "wörkers".to_owned());
    assert!(matches!(
        StableElementResolverV1::seal(
            &value.graph,
            "demo/world",
            &non_ascii,
            &value.hyperedge_names,
        ),
        Err(StableIdentityError::InvalidString {
            field: "node local name",
            ..
        })
    ));

    let mut missing_hyperedge = value.hyperedge_names.clone();
    missing_hyperedge.remove(&value.coalition_a);
    assert_eq!(
        StableElementResolverV1::seal(
            &value.graph,
            "demo/world",
            &value.node_names,
            &missing_hyperedge,
        ),
        Err(StableIdentityError::MissingHyperedgeName {
            hyperedge: value.coalition_a,
        })
    );

    let mut duplicate_hyperedge = value.hyperedge_names.clone();
    duplicate_hyperedge.insert(value.coalition_b, "coalition-a".to_owned());
    assert_eq!(
        StableElementResolverV1::seal(
            &value.graph,
            "demo/world",
            &value.node_names,
            &duplicate_hyperedge,
        ),
        Err(StableIdentityError::DuplicateHyperedgeName {
            local_name: "coalition-a".to_owned(),
        })
    );

    let mut extra_hyperedge = value.hyperedge_names.clone();
    extra_hyperedge.insert(HyperedgeId(999), "ghost-group".to_owned());
    assert_eq!(
        StableElementResolverV1::seal(
            &value.graph,
            "demo/world",
            &value.node_names,
            &extra_hyperedge,
        ),
        Err(StableIdentityError::ExtraHyperedgeName {
            hyperedge: HyperedgeId(999),
        })
    );
}

#[test]
fn resolver_refuses_dangling_edges_and_never_falls_back_to_runtime_ids() {
    let value = fixture();
    let resolver = resolver(&value);
    assert_eq!(
        resolver.node_key(NodeId(999)),
        Err(StableIdentityError::UnknownNode { node: NodeId(999) })
    );
    assert_eq!(
        resolver.edge_key("solidarity", value.owners, value.workers),
        Err(StableIdentityError::UnknownEdge {
            edge_type: "solidarity".to_owned(),
            source: value.owners,
            target: value.workers,
        })
    );

    let mut dangling_names = value.node_names.clone();
    dangling_names.remove(&value.owners);
    dangling_names.insert(NodeId(999), "owners".to_owned());
    assert_eq!(
        StableElementResolverV1::seal(
            &value.graph,
            "demo/world",
            &dangling_names,
            &value.hyperedge_names,
        ),
        Err(StableIdentityError::MissingNodeName { node: value.owners })
    );
}

#[test]
fn sealed_resolver_detects_every_topology_mutation() {
    let value = fixture();
    let resolver = resolver(&value);
    resolver.validate_topology(&value.graph).unwrap();

    let mut added = value.graph.clone();
    added.add_node("class").unwrap();
    assert_eq!(
        resolver.validate_topology(&added),
        Err(StableIdentityError::TopologyChanged)
    );

    let mut removed = value.graph.clone();
    removed.remove_node(value.owners).unwrap();
    assert_eq!(
        resolver.validate_topology(&removed),
        Err(StableIdentityError::TopologyChanged)
    );

    let mut edge_removed = value.graph.clone();
    edge_removed
        .remove_edge("solidarity", value.workers, value.owners)
        .unwrap();
    assert_eq!(
        resolver.validate_topology(&edge_removed),
        Err(StableIdentityError::TopologyChanged)
    );

    let mut membership_changed = value.graph.clone();
    membership_changed
        .remove_hyperedge(value.coalition_a)
        .unwrap();
    membership_changed
        .add_hyperedge("coalition", &[value.workers])
        .unwrap();
    assert_eq!(
        resolver.validate_topology(&membership_changed),
        Err(StableIdentityError::TopologyChanged)
    );
}

#[test]
fn resolver_accepts_65536_rows_and_refuses_65537_before_manifest_allocation() {
    let mut graph = MemoryGraph::new();
    let mut names = HashMap::new();
    for index in 0..MAX_STABLE_RESOLVER_ROWS_V1 {
        let node = graph.add_node("class").unwrap();
        names.insert(node, format!("n{index}"));
    }
    let maximum =
        StableElementResolverV1::seal(&graph, "demo/world", &names, &HashMap::new()).unwrap();
    assert!(maximum.manifest().canonical_bytes().len() <= MAX_STABLE_RESOLVER_MANIFEST_BYTES_V1);

    let extra = graph.add_node("class").unwrap();
    names.insert(extra, "overflow".to_owned());
    assert_eq!(
        StableElementResolverV1::seal(&graph, "demo/world", &names, &HashMap::new(),),
        Err(StableIdentityError::ResolverRowLimit {
            actual: MAX_STABLE_RESOLVER_ROWS_V1 + 1,
            maximum: MAX_STABLE_RESOLVER_ROWS_V1,
        })
    );
}

#[test]
fn forged_stable_element_cannot_enter_a_resolver_owned_carrier() {
    let value = fixture();
    let resolver = resolver(&value);
    let forged = StableElementKeyV1::Node {
        scenario: "demo/world".to_owned(),
        local_name: "ghost".to_owned(),
    };
    assert_eq!(
        resolver.carrier_key(&forged, &[], 0),
        Err(StableIdentityError::ElementNotSealed)
    );
}
