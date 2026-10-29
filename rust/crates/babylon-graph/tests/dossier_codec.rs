use babylon_graph::dossier::Dossier;
use babylon_graph::exposure::{components, ExposureGraph};
use babylon_graph::substrate::{Direction, NodeId};

fn fixture() -> Dossier {
    let mut dossier = Dossier::new(NodeId(7));
    dossier.resolve_edge("z", NodeId(3), NodeId(1));
    dossier.resolve_edge("a", NodeId(1), NodeId(2));
    dossier.resolve_node(NodeId(4));
    dossier
}

fn bytes(owner: u64, nodes: &[u64], edges: &[(&[u8], u64, u64)]) -> Vec<u8> {
    let mut out = b"babylon.dossier\0\0\0\0\x01".to_vec();
    out.extend_from_slice(&owner.to_be_bytes());
    out.extend_from_slice(
        &u32::try_from(nodes.len())
            .expect("fixture node count fits")
            .to_be_bytes(),
    );
    for node in nodes {
        out.extend_from_slice(&node.to_be_bytes());
    }
    out.extend_from_slice(
        &u32::try_from(edges.len())
            .expect("fixture edge count fits")
            .to_be_bytes(),
    );
    for (kind, from, to) in edges {
        out.extend_from_slice(
            &u32::try_from(kind.len())
                .expect("fixture type length fits")
                .to_be_bytes(),
        );
        out.extend_from_slice(kind);
        out.extend_from_slice(&from.to_be_bytes());
        out.extend_from_slice(&to.to_be_bytes());
    }
    out
}

#[test]
fn canonical_round_trip_is_order_independent_and_retains_private_direction() {
    let empty = Dossier::new(NodeId(8));
    assert_eq!(
        empty.encode_canonical().expect("empty dossier"),
        bytes(8, &[], &[])
    );
    assert_eq!(
        Dossier::decode_canonical(&bytes(8, &[], &[])).expect("empty dossier"),
        empty
    );
    let dossier = fixture();
    let expected = bytes(7, &[1, 2, 3, 4], &[(b"a", 1, 2), (b"z", 3, 1)]);
    assert_eq!(
        dossier.encode_canonical().expect("valid dossier fixture"),
        expected
    );
    let restored = Dossier::decode_canonical(&expected).expect("valid dossier fixture");
    assert_eq!(restored, dossier);
    assert_eq!(
        restored
            .neighbors(NodeId(1), "a", Direction::Out)
            .expect("valid dossier fixture"),
        vec![NodeId(2)]
    );
    assert_eq!(
        components(&restored, &restored.scope(), "a").expect("valid dossier fixture"),
        vec![vec![NodeId(1), NodeId(2)], vec![NodeId(3)], vec![NodeId(4)]]
    );
    let mut reordered = Dossier::new(NodeId(7));
    reordered.resolve_node(NodeId(4));
    reordered.resolve_edge("a", NodeId(1), NodeId(2));
    reordered.resolve_edge("z", NodeId(3), NodeId(1));
    assert_eq!(
        reordered.encode_canonical().expect("valid dossier fixture"),
        expected
    );
    reordered.resolve_edge("a", NodeId(2), NodeId(3));
    assert!(!restored.knows_edge("a", NodeId(2), NodeId(3)));
}

#[test]
fn rejects_malformed_noncanonical_and_dangling_rows() {
    let valid = bytes(7, &[1, 2], &[(b"a", 1, 2)]);
    for end in 0..valid.len() {
        assert!(
            Dossier::decode_canonical(&valid[..end]).is_err(),
            "truncation at {end}"
        );
    }
    let mut trailing = valid.clone();
    trailing.push(0);
    let mut huge_count = bytes(7, &[], &[]);
    huge_count[28..32].copy_from_slice(&u32::MAX.to_be_bytes());
    let mut huge_edges = bytes(7, &[], &[]);
    huge_edges[32..36].copy_from_slice(&u32::MAX.to_be_bytes());
    let mut wrong_header = valid.clone();
    wrong_header[0] = b'X';
    let cases = [
        trailing,
        huge_count,
        huge_edges,
        wrong_header,
        vec![0; 16_777_217],
        bytes(u64::MAX, &[], &[]),
        bytes(7, &[1, 1], &[]),
        bytes(7, &[2, 1], &[]),
        bytes(7, &[u64::MAX], &[]),
        bytes(7, &[1, 2], &[(b"a", 1, 2), (b"a", 1, 2)]),
        bytes(7, &[1, 2], &[(b"z", 1, 2), (b"a", 1, 2)]),
        bytes(7, &[1], &[(b"a", 1, 2)]),
        bytes(7, &[1, 2], &[(b"", 1, 2)]),
        bytes(7, &[1, 2], &[(&[0xff], 1, 2)]),
        bytes(7, &[1, 2], &[(&[b'x'; 129], 1, 2)]),
    ];
    for bad in cases {
        assert!(Dossier::decode_canonical(&bad).is_err(), "accepted {bad:?}");
    }
    let mut invalid = Dossier::new(NodeId(7));
    invalid.resolve_edge("", NodeId(1), NodeId(2));
    assert!(invalid.encode_canonical().is_err());
}
