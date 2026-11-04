use babylon_graph::dossier::Dossier;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::stable_element::StableElementResolver;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use std::collections::HashMap;

#[derive(Clone, Copy)]
enum AllocationOrder {
    Original,
    Reordered,
}

fn substrate(
    order: AllocationOrder,
) -> (MemoryGraph, StableElementResolver, NodeId, NodeId, NodeId) {
    let mut graph = MemoryGraph::new();
    let mut names = HashMap::new();
    if matches!(order, AllocationOrder::Reordered) {
        let hidden = graph.add_node("actor").expect("hidden node");
        names.insert(hidden, "unrelated".to_owned());
    }
    let first = graph.add_node("actor").expect("first node");
    let second = graph.add_node("actor").expect("second node");
    let third = graph.add_node("actor").expect("third node");
    let (owner, alpha, beta) = if matches!(order, AllocationOrder::Reordered) {
        (third, second, first)
    } else {
        (first, second, third)
    };
    names.insert(owner, "agency".to_owned());
    names.insert(alpha, "alpha".to_owned());
    names.insert(beta, "beta".to_owned());
    let resolver = StableElementResolver::seal(&graph, "demo/world", &names, &HashMap::new())
        .expect("sealed fixture");
    (graph, resolver, owner, alpha, beta)
}
fn frame(out: &mut Vec<u8>, bytes: &[u8]) {
    out.extend_from_slice(
        &u32::try_from(bytes.len())
            .expect("valid identity test fixture")
            .to_be_bytes(),
    );
    out.extend_from_slice(bytes);
}
// Independent literal wire fixture; stable keys use the separately governed key layout.
fn key(name: &str) -> Vec<u8> {
    let mut out = b"babylon.stable-element\0\0\0\0\x01\x01".to_vec();
    frame(&mut out, b"demo/world");
    frame(&mut out, name.as_bytes());
    out
}
fn bytes(owner: &str, nodes: &[&str], edges: &[(&[u8], &str, &str)]) -> Vec<u8> {
    let mut out = b"babylon.dossier\0\0\0\0\x02".to_vec();
    frame(&mut out, &key(owner));
    out.extend_from_slice(
        &u32::try_from(nodes.len())
            .expect("valid identity test fixture")
            .to_be_bytes(),
    );
    for node in nodes {
        frame(&mut out, &key(node));
    }
    out.extend_from_slice(
        &u32::try_from(edges.len())
            .expect("valid identity test fixture")
            .to_be_bytes(),
    );
    for (kind, from, to) in edges {
        frame(&mut out, kind);
        frame(&mut out, &key(from));
        frame(&mut out, &key(to));
    }
    out
}
#[test]
fn canonical_fixture_round_trips_and_rejects_noncanonical_input() {
    let (_, resolver, owner, alpha, beta) = substrate(AllocationOrder::Original);
    let mut dossier = Dossier::new(owner);
    dossier.resolve_edge("false", alpha, beta);
    // Canonical key bytes sort the shorter local name before the longer one.
    let expected = bytes("agency", &["beta", "alpha"], &[(b"false", "alpha", "beta")]);
    assert_eq!(
        dossier
            .encode_canonical(&resolver)
            .expect("valid identity test fixture"),
        expected
    );
    assert_eq!(
        Dossier::decode_canonical(&expected, &resolver).expect("valid identity test fixture"),
        dossier
    );
    let mut reordered = Dossier::new(owner);
    reordered.resolve_node(beta);
    reordered.resolve_node(alpha);
    reordered.resolve_edge("false", alpha, beta);
    assert_eq!(
        reordered
            .encode_canonical(&resolver)
            .expect("valid identity test fixture"),
        expected
    );
    for end in 0..expected.len() {
        assert!(Dossier::decode_canonical(&expected[..end], &resolver).is_err());
    }
    let mut trailing = expected.clone();
    trailing.push(0);
    let mut huge = expected.clone();
    huge[19..23].copy_from_slice(&u32::MAX.to_be_bytes());
    let mut non_node = expected.clone();
    let tag_offset = 19 + 4 + b"babylon.stable-element".len() + 1 + 4;
    non_node[tag_offset] = 3;
    let cases = [
        trailing,
        huge,
        non_node,
        vec![0; 16_777_217],
        b"babylon.dossier\0\0\0\0\x01".to_vec(),
        bytes("agency", &["beta", "beta"], &[]),
        bytes("agency", &["alpha", "beta"], &[]),
        bytes("agency", &["alpha"], &[(b"false", "alpha", "beta")]),
        bytes(
            "agency",
            &["beta", "alpha"],
            &[(b"false", "alpha", "beta"), (b"false", "alpha", "beta")],
        ),
        bytes("agency", &["beta", "alpha"], &[(b"", "alpha", "beta")]),
        bytes(
            "agency",
            &["beta", "alpha"],
            &[(&[b'x'; 129], "alpha", "beta")],
        ),
        bytes("agency", &["beta", "alpha"], &[(&[0xff], "alpha", "beta")]),
        bytes("missing", &[], &[]),
    ];
    for bad in cases {
        assert!(Dossier::decode_canonical(&bad, &resolver).is_err());
    }
    let mut invalid = Dossier::new(owner);
    invalid.resolve_edge("", alpha, beta);
    assert!(invalid.encode_canonical(&resolver).is_err());
    assert!(Dossier::new(NodeId(u64::MAX))
        .encode_canonical(&resolver)
        .is_err());
    let (foreign_graph, _, _, _, _) = substrate(AllocationOrder::Original);
    let names = HashMap::from([
        (NodeId(0), "agency".to_owned()),
        (NodeId(1), "alpha".to_owned()),
        (NodeId(2), "beta".to_owned()),
    ]);
    let foreign =
        StableElementResolver::seal(&foreign_graph, "other/world", &names, &HashMap::new())
            .expect("valid identity test fixture");
    assert!(Dossier::decode_canonical(&expected, &foreign).is_err());
}
#[test]
fn semantically_identical_dossiers_survive_handle_reallocation() {
    let (_, resolver_a, owner_a, alpha_a, beta_a) = substrate(AllocationOrder::Original);
    let (mut graph_b, resolver_b, owner_b, alpha_b, beta_b) = substrate(AllocationOrder::Reordered);
    assert_ne!(owner_a, owner_b);
    let mut first = Dossier::new(owner_a);
    first.resolve_edge("believed-only", alpha_a, beta_a);
    let mut second = Dossier::new(owner_b);
    second.resolve_edge("believed-only", alpha_b, beta_b);
    graph_b
        .remove_node(beta_b)
        .expect("valid identity test fixture");
    let first_bytes = first
        .encode_canonical(&resolver_a)
        .expect("valid identity test fixture");
    assert_eq!(
        first_bytes,
        second
            .encode_canonical(&resolver_b)
            .expect("valid identity test fixture")
    );
    let restored =
        Dossier::decode_canonical(&first_bytes, &resolver_b).expect("valid identity test fixture");
    assert_eq!(restored.owner(), owner_b);
    assert!(restored.knows_node(alpha_b));
    assert!(restored.knows_node(beta_b));
    assert!(restored.knows_edge("believed-only", alpha_b, beta_b));
    assert_eq!(restored.stale_nodes(&graph_b), vec![beta_b]);
}
