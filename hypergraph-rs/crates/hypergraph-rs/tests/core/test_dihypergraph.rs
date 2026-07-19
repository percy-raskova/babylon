//! Unit tests for `DiHypergraph` — mirroring XGI's
//! `tests/core/test_dihypergraph.py`.

use hypergraph_rs::{DiHypergraph, Direction, EdgeError, MembershipError, NodeError};
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

// ---------------------------------------------------------------------------
// Membership ops and removals (Phase 2 Task 4)
// ---------------------------------------------------------------------------

#[test]
fn add_node_to_edge_autocreates_edge_and_node() {
    // XGI parity: auto-creates a missing edge AND a missing node;
    // direction In -> tail, Out -> head. Infallible () like the
    // undirected core (Task 1 signature mirror).
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node_to_edge("e1", "a", Direction::In);
    assert!(h.has_edge("e1"));
    assert!(h.has_node("a"));
    assert_eq!(h.tail("e1").unwrap(), vec!["a"]);
    assert_eq!(h.head("e1").unwrap(), Vec::<String>::new());
    // Auto-created edge/node carry default attrs.
    assert_eq!(h.edge_attrs("e1").unwrap(), &Value::Null);
    assert_eq!(h.node_attrs("a").unwrap(), &Value::Null);

    h.add_node_to_edge("e2", "b", Direction::Out);
    assert_eq!(h.tail("e2").unwrap(), Vec::<String>::new());
    assert_eq!(h.head("e2").unwrap(), vec!["b"]);
}

#[test]
fn add_node_to_edge_numeric_id_bumps_counter() {
    // D11-extension: XGI's DiHypergraph.add_node_to_edge does NOT bump
    // the uid counter (probed: next auto id 0 after auto-creating edge
    // 5); the Rust core bumps iff the id parses as u64 — the D3/D11 rule
    // extended to DiHypergraph.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node_to_edge("5", "x", Direction::In);
    let auto = h
        .add_edge((vec!["y".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "6");
    // Non-numeric ids don't bump.
    let mut h2: DiHypergraph = DiHypergraph::new();
    h2.add_node_to_edge("e", "x", Direction::In);
    let auto2 = h2
        .add_edge((vec!["y".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(auto2, "0");
}

#[test]
fn add_node_to_edge_set_semantics_and_both_directions() {
    // Re-adding the same (node, direction) is a no-op; adding the same
    // node in the OTHER direction puts it in BOTH sets (probed).
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_node_to_edge("e1", "a", Direction::In); // already tail: no-op
    assert_eq!(h.tail("e1").unwrap(), vec!["a"]);
    assert_eq!(h.head("e1").unwrap(), vec!["b"]);
    h.add_node_to_edge("e1", "a", Direction::Out); // now BOTH
    assert_eq!(h.tail("e1").unwrap(), vec!["a"]);
    assert_eq!(h.head("e1").unwrap(), vec!["a", "b"]);
    assert_eq!(
        h.dimemberships("a").unwrap(),
        (vec!["e1".to_string()], vec!["e1".to_string()])
    );
}

#[test]
fn remove_node_from_edge_removes_only_that_direction() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["b".into(), "c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.remove_node_from_edge("e1", "b", Direction::In, false)
        .unwrap();
    assert_eq!(h.tail("e1").unwrap(), vec!["a"]);
    assert_eq!(h.head("e1").unwrap(), vec!["b", "c"]); // b survives in head
                                                       // Removing the OTHER direction now removes b entirely.
    h.remove_node_from_edge("e1", "b", Direction::Out, false)
        .unwrap();
    assert_eq!(h.head("e1").unwrap(), vec!["c"]);
}

#[test]
fn remove_node_from_edge_emptied_means_both_sides() {
    // Directed "emptied" = BOTH tail AND head empty (probed): removing
    // the last tail member of ([a],[b]) with remove_empty=true leaves the
    // edge ALIVE (head still populated).
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.remove_node_from_edge("e1", "a", Direction::In, true)
        .unwrap();
    assert!(h.has_edge("e1"));
    assert_eq!(
        h.dimembers("e1").unwrap(),
        (Vec::<String>::new(), vec!["b".to_string()])
    );
    // Removing the last head member empties both sides -> dropped.
    h.remove_node_from_edge("e1", "b", Direction::Out, true)
        .unwrap();
    assert!(!h.has_edge("e1"));
    assert!(h.has_node("a") && h.has_node("b")); // nodes survive
}

#[test]
fn remove_node_from_edge_keep_empty() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge((vec!["a".into()], vec![]), Some("e1".into()), Value::Null)
        .unwrap();
    h.remove_node_from_edge("e1", "a", Direction::In, false)
        .unwrap();
    assert!(h.has_edge("e1"));
    assert_eq!(
        h.dimembers("e1").unwrap(),
        (Vec::<String>::new(), Vec::<String>::new())
    );
}

#[test]
fn remove_node_from_edge_membership_errors() {
    // Missing edge.
    let mut h: DiHypergraph = DiHypergraph::new();
    let err = h.remove_node_from_edge("noedge", "a", Direction::In, true);
    assert_eq!(
        err,
        Err(MembershipError::EdgeNotFound {
            edge_id: "noedge".to_string()
        })
    );
    assert_eq!(err.unwrap_err().to_string(), "edge noedge does not exist");
    // Missing node.
    h.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    assert_eq!(
        h.remove_node_from_edge("e1", "ghost", Direction::Out, true),
        Err(MembershipError::NodeNotFound {
            node_id: "ghost".to_string()
        })
    );
    // Not a member IN THAT DIRECTION (b is head-only; In fails).
    assert_eq!(
        h.remove_node_from_edge("e1", "b", Direction::In, true),
        Err(MembershipError::NotAMember {
            node_id: "b".to_string(),
            edge_id: "e1".to_string()
        })
    );
    let err = h.remove_node_from_edge("e1", "a", Direction::Out, true);
    assert_eq!(
        err,
        Err(MembershipError::NotAMember {
            node_id: "a".to_string(),
            edge_id: "e1".to_string()
        })
    );
    assert_eq!(
        err.unwrap_err().to_string(),
        "node a is not a member of edge e1"
    );
}

#[test]
fn remove_edge_basic_and_missing() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge((vec!["c".into()], vec![]), Some("e2".into()), Value::Null)
        .unwrap();
    h.remove_edge("e1").unwrap();
    assert_eq!(h.edge_ids(), vec!["e2"]);
    assert_eq!(h.num_nodes(), 3); // nodes survive
    assert_eq!(h.memberships("a").unwrap(), Vec::<String>::new());
    assert!(matches!(
        h.remove_edge("ghost"),
        Err(EdgeError::NotFound { .. })
    ));
}

#[test]
fn remove_edges_from_per_item_stops_after_err() {
    // D2-class translation (probed XGI raises mid-iteration; partial
    // effects): per-item results, stop after the first Err.
    let mut h: DiHypergraph = DiHypergraph::new();
    for e in ["e1", "e2", "e3"] {
        h.add_edge((vec!["a".into()], vec![]), Some(e.into()), Value::Null)
            .unwrap();
    }
    let results = h.remove_edges_from(vec![
        "e1".to_string(),
        "ghost".to_string(),
        "e3".to_string(),
    ]);
    assert_eq!(results.len(), 2);
    assert!(results[0].is_ok());
    assert!(matches!(results[1], Err(EdgeError::NotFound { .. })));
    assert_eq!(h.edge_ids(), vec!["e2", "e3"]);
}

#[test]
fn remove_node_weak_both_directions() {
    // Weak removal drops the node from BOTH directions of every edge.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["b".into(), "c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["b".into()], vec!["d".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["e".into()], vec!["b".into()]),
        Some("e3".into()),
        Value::Null,
    )
    .unwrap();
    h.remove_node("b", false, false).unwrap();
    assert!(!h.has_node("b"));
    assert_eq!(
        h.dimembers("e1").unwrap(),
        (vec!["a".to_string()], vec!["c".to_string()])
    );
    assert_eq!(
        h.dimembers("e2").unwrap(),
        (Vec::<String>::new(), vec!["d".to_string()])
    );
    assert_eq!(
        h.dimembers("e3").unwrap(),
        (vec!["e".to_string()], Vec::<String>::new())
    );
}

#[test]
fn remove_node_weak_drops_only_both_empty_edges() {
    // remove_empty=true: e2 (tail-only singleton) empties BOTH sides ->
    // dropped; e1 keeps its head -> survives.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["b".into()], vec!["d".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge((vec!["b".into()], vec![]), Some("e2".into()), Value::Null)
        .unwrap();
    h.remove_node("b", false, true).unwrap();
    assert_eq!(h.edge_ids(), vec!["e1"]);
    assert_eq!(
        h.dimembers("e1").unwrap(),
        (Vec::<String>::new(), vec!["d".to_string()])
    );
}

#[test]
fn remove_node_weak_remove_empty_false_keeps_emptied_edge() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge((vec!["b".into()], vec![]), Some("e1".into()), Value::Null)
        .unwrap();
    h.remove_node("b", false, false).unwrap();
    assert_eq!(h.edge_ids(), vec!["e1"]);
    assert_eq!(
        h.dimembers("e1").unwrap(),
        (Vec::<String>::new(), Vec::<String>::new())
    );
}

#[test]
fn remove_node_strong_removes_incident_edges_regardless_of_flag() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["d".into()], vec!["b".into(), "e".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["f".into()], vec!["g".into()]),
        Some("e3".into()),
        Value::Null,
    )
    .unwrap();
    h.remove_node("b", true, false).unwrap();
    assert_eq!(h.edge_ids(), vec!["e3"]);
    // Other nodes survive the strong removal of incident edges.
    for n in ["a", "c", "d", "e", "f", "g"] {
        assert!(h.has_node(n));
    }
    assert!(!h.has_node("b"));
}

#[test]
fn remove_node_missing_returns_error() {
    let mut h: DiHypergraph = DiHypergraph::new();
    assert!(matches!(
        h.remove_node("ghost", false, true),
        Err(NodeError::NotFound { .. })
    ));
}

#[test]
fn remove_nodes_from_per_item_continues_past_missing() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    let results = h.remove_nodes_from(
        vec!["a".to_string(), "ghost".to_string(), "b".to_string()],
        false,
        true,
    );
    assert_eq!(results.len(), 3);
    assert!(results[0].is_ok());
    assert!(matches!(results[1], Err(NodeError::NotFound { .. })));
    assert!(results[2].is_ok());
    assert_eq!(h.node_ids(), vec!["c"]);
    // Tail emptied but head survives -> e1 lives.
    assert_eq!(
        h.dimembers("e1").unwrap(),
        (Vec::<String>::new(), vec!["c".to_string()])
    );
}
