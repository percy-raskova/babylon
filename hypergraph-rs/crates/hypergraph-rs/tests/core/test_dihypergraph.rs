//! Unit tests for `DiHypergraph` — mirroring XGI's
//! `tests/core/test_dihypergraph.py`.

use hypergraph_rs::{DiHypergraph, Direction};
use serde_json::Value;

/// Two-edge fixture used across the query tests:
/// e1 = ([a, b], [b, c]) — b is in BOTH directions; e2 = ([c], [a]).
fn two_edge_fixture() -> DiHypergraph {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["b".into(), "c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["c".into()], vec!["a".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h
}

#[test]
fn new_is_empty() {
    let h: DiHypergraph = DiHypergraph::new();
    assert_eq!(h.num_nodes(), 0);
    assert_eq!(h.num_edges(), 0);
    assert!(h.node_ids().is_empty());
    assert!(h.edge_ids().is_empty());
}

#[test]
fn add_node_returns_bool_and_replaces_attrs() {
    // D6 parity with the undirected core: re-adding an existing node
    // REPLACES its attrs (XGI merges; a generic N cannot — the binding
    // merges before calling).
    let mut h: DiHypergraph = DiHypergraph::new();
    assert!(h.add_node("a", serde_json::json!({"x": 1})));
    assert!(!h.add_node("a", serde_json::json!({"y": 2})));
    assert_eq!(h.num_nodes(), 1);
    assert_eq!(h.node_attrs("a").unwrap(), &serde_json::json!({"y": 2}));
}

#[test]
fn add_nodes_from_bulk() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_nodes_from(vec![
        ("a".to_string(), Value::Null),
        ("b".to_string(), Value::Null),
    ]);
    assert_eq!(h.node_ids(), vec!["a", "b"]);
}

#[test]
fn has_node_and_attrs() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node("a", serde_json::json!({"k": 1}));
    assert!(h.has_node("a"));
    assert!(!h.has_node("ghost"));
    assert_eq!(h.node_attrs("a").unwrap(), &serde_json::json!({"k": 1}));
    assert!(h.node_attrs("ghost").is_none());
}

#[test]
fn add_edge_auto_id_and_attrs() {
    let mut h: DiHypergraph = DiHypergraph::new();
    let eid = h
        .add_edge(
            (vec!["a".into()], vec!["b".into()]),
            None,
            serde_json::json!({"w": 1}),
        )
        .unwrap();
    assert_eq!(eid, "0");
    assert!(h.has_edge("0"));
    assert!(!h.has_edge("ghost"));
    assert_eq!(h.edge_attrs("0").unwrap(), &serde_json::json!({"w": 1}));
    assert!(h.edge_attrs("ghost").is_none());
}

#[test]
fn add_edge_auto_creates_missing_nodes() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["b".into(), "c".into()]),
        None,
        Value::Null,
    )
    .unwrap();
    assert_eq!(h.node_ids(), vec!["a", "b", "c"]);
    // Auto-created nodes carry default attrs.
    assert_eq!(h.node_attrs("a").unwrap(), &Value::Null);
}

#[test]
fn add_edge_dedups_within_each_direction() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (
            vec!["a".into(), "a".into(), "b".into()],
            vec!["b".into(), "b".into(), "c".into()],
        ),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    assert_eq!(h.tail("e1").unwrap(), vec!["a", "b"]);
    assert_eq!(h.head("e1").unwrap(), vec!["b", "c"]);
}

#[test]
fn tail_head_dimembers_queries() {
    let h = two_edge_fixture();
    assert_eq!(h.tail("e1").unwrap(), vec!["a", "b"]);
    assert_eq!(h.head("e1").unwrap(), vec!["b", "c"]);
    assert_eq!(
        h.dimembers("e1").unwrap(),
        (
            vec!["a".to_string(), "b".to_string()],
            vec!["b".to_string(), "c".to_string()]
        )
    );
    assert_eq!(h.tail("e2").unwrap(), vec!["c"]);
    assert_eq!(h.head("e2").unwrap(), vec!["a"]);
}

#[test]
fn members_is_union_in_insertion_order() {
    // members(e) = tail ∪ head, node-insertion order, deduped (D5).
    let h = two_edge_fixture();
    assert_eq!(h.members("e1").unwrap(), vec!["a", "b", "c"]);
    assert_eq!(h.members("e2").unwrap(), vec!["a", "c"]);
}

#[test]
fn dimemberships_is_in_out_order() {
    // (in, out): "in" = edges where the node is in the HEAD, "out" =
    // edges where the node is in the TAIL — IN FIRST (probed XGI order).
    let h = two_edge_fixture();
    // a: tail of e2, head of e1? No — a is in TAIL of e1 and HEAD of e2.
    assert_eq!(
        h.dimemberships("a").unwrap(),
        (vec!["e2".to_string()], vec!["e1".to_string()])
    );
    // b: BOTH directions of e1.
    assert_eq!(
        h.dimemberships("b").unwrap(),
        (vec!["e1".to_string()], vec!["e1".to_string()])
    );
    // c: head of e1, tail of e2.
    assert_eq!(
        h.dimemberships("c").unwrap(),
        (vec!["e1".to_string()], vec!["e2".to_string()])
    );
}

#[test]
fn memberships_is_union() {
    let h = two_edge_fixture();
    assert_eq!(h.memberships("a").unwrap(), vec!["e1", "e2"]);
    assert_eq!(h.memberships("b").unwrap(), vec!["e1"]);
}

#[test]
fn missing_id_queries_return_none() {
    let h = two_edge_fixture();
    assert!(h.tail("ghost").is_none());
    assert!(h.head("ghost").is_none());
    assert!(h.dimembers("ghost").is_none());
    assert!(h.members("ghost").is_none());
    assert!(h.dimemberships("ghost").is_none());
    assert!(h.memberships("ghost").is_none());
}

#[test]
fn queries_are_insertion_ordered_under_interleaved_adds() {
    // D5/III.7: bimap-filter order, never neighbor-LIFO order.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["n1".into()], vec!["n2".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["n2".into()], vec!["n1".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["n3".into()], vec!["n1".into()]),
        Some("e3".into()),
        Value::Null,
    )
    .unwrap();
    // n1 insertion-precedes n2/n3; edge insertion order e1, e2, e3.
    assert_eq!(h.node_ids(), vec!["n1", "n2", "n3"]);
    assert_eq!(h.edge_ids(), vec!["e1", "e2", "e3"]);
    // n1: tail of e1; head of e2 and e3.
    assert_eq!(
        h.dimemberships("n1").unwrap(),
        (
            vec!["e2".to_string(), "e3".to_string()],
            vec!["e1".to_string()]
        )
    );
    assert_eq!(h.head("e2").unwrap(), vec!["n1"]);
    assert_eq!(h.tail("e3").unwrap(), vec!["n3"]);
}

#[test]
fn graph_attrs_roundtrip() {
    let mut h: DiHypergraph = DiHypergraph::new();
    assert!(h.graph_attr("name").is_none());
    h.set_graph_attr("name", serde_json::json!("test"));
    assert_eq!(h.graph_attr("name").unwrap(), &serde_json::json!("test"));
}

#[test]
fn empty_directed_edge_is_allowed() {
    // D1-class parity: an empty (tail, head) pair creates an empty edge.
    let mut h: DiHypergraph = DiHypergraph::new();
    let eid = h.add_edge((vec![], vec![]), None, Value::Null).unwrap();
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.num_nodes(), 0);
    assert_eq!(
        h.dimembers(&eid).unwrap(),
        (Vec::<String>::new(), Vec::<String>::new())
    );
}

#[test]
fn direction_enum_serializes_lowercase() {
    // The Phase 7 binding maps XGI's "in"/"out" direction strings onto
    // the enum; pin the serde spelling so the mapping is stable.
    assert_eq!(serde_json::to_string(&Direction::In).unwrap(), "\"in\"");
    assert_eq!(serde_json::to_string(&Direction::Out).unwrap(), "\"out\"");
    assert_eq!(
        serde_json::from_str::<Direction>("\"in\"").unwrap(),
        Direction::In
    );
    assert_eq!(
        serde_json::from_str::<Direction>("\"out\"").unwrap(),
        Direction::Out
    );
}
