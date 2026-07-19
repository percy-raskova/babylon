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

// ---------------------------------------------------------------------------
// Bulk add, attributes, copy/clear/freeze, Debug, PartialEq (Phase 2 Task 5)
// ---------------------------------------------------------------------------

#[test]
fn add_edges_from_bulk_and_auto_ids() {
    let mut h: DiHypergraph = DiHypergraph::new();
    let results = h.add_edges_from(vec![
        (
            vec!["a".into(), "b".into()],
            vec!["c".into()],
            None,
            Value::Null,
        ),
        (
            vec!["d".into()],
            vec![],
            Some("named".into()),
            serde_json::json!({"w": 1}),
        ),
        (vec!["e".into()], vec!["f".into()], None, Value::Null),
    ]);
    assert_eq!(results.len(), 3);
    assert_eq!(results[0].as_ref().unwrap(), "0");
    assert_eq!(results[1].as_ref().unwrap(), "named");
    assert_eq!(results[2].as_ref().unwrap(), "1");
    assert_eq!(h.edge_ids(), vec!["0", "named", "1"]);
    assert_eq!(h.tail("0").unwrap(), vec!["a", "b"]);
    assert_eq!(h.head("0").unwrap(), vec!["c"]);
    assert_eq!(h.edge_attrs("named").unwrap(), &serde_json::json!({"w": 1}));
}

#[test]
fn add_edges_from_dup_errors_and_continues() {
    // D2-class: the dup surfaces as Err(AlreadyExists); the bunch
    // continues; the dup's members are never added.
    let mut h: DiHypergraph = DiHypergraph::new();
    let results = h.add_edges_from(vec![
        (
            vec!["a".into()],
            vec!["b".into()],
            Some("e1".into()),
            Value::Null,
        ),
        (
            vec!["c".into()],
            vec!["d".into()],
            Some("e1".into()),
            Value::Null,
        ),
        (
            vec!["e".into()],
            vec!["f".into()],
            Some("e2".into()),
            Value::Null,
        ),
    ]);
    assert!(results[0].is_ok());
    assert!(matches!(results[1], Err(EdgeError::AlreadyExists { .. })));
    assert!(results[2].is_ok());
    assert_eq!(h.edge_ids(), vec!["e1", "e2"]);
    assert!(!h.has_node("c"));
}

#[test]
fn add_edges_from_creates_empty_edge() {
    // D1-class parity: ([], []) inside a bulk add creates an empty edge.
    let mut h: DiHypergraph = DiHypergraph::new();
    let results = h.add_edges_from(vec![
        (vec![], vec![], None, Value::Null),
        (vec!["a".into()], vec!["b".into()], None, Value::Null),
    ]);
    assert!(results.iter().all(|r| r.is_ok()));
    assert_eq!(h.num_edges(), 2);
    assert_eq!(
        h.dimembers("0").unwrap(),
        (Vec::<String>::new(), Vec::<String>::new())
    );
}

#[test]
fn attrs_mut_write_through() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node("a", serde_json::json!({}));
    h.add_edge(
        (vec!["a".into()], vec![]),
        Some("e1".into()),
        serde_json::json!({}),
    )
    .unwrap();
    h.node_attrs_mut("a").unwrap()["color"] = serde_json::json!("red");
    h.edge_attrs_mut("e1").unwrap()["heat"] = serde_json::json!(0.5);
    assert_eq!(h.node_attrs("a").unwrap()["color"], "red");
    assert_eq!(h.edge_attrs("e1").unwrap()["heat"], 0.5);
    assert!(h.node_attrs_mut("ghost").is_none());
    assert!(h.edge_attrs_mut("ghost").is_none());
}

#[test]
fn set_node_attributes_merges_skips_missing() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node("a", serde_json::json!({"x": 1}));
    h.add_node("b", Value::Null); // non-object slot -> REPLACED
    let color = |c: &str| {
        let mut m = serde_json::Map::new();
        m.insert("color".to_string(), serde_json::json!(c));
        m
    };
    h.set_node_attributes(vec![
        ("a".to_string(), color("red")),
        ("b".to_string(), color("blue")),
        ("ghost".to_string(), color("green")),
    ]);
    assert_eq!(
        h.node_attrs("a").unwrap(),
        &serde_json::json!({"x": 1, "color": "red"})
    );
    assert_eq!(
        h.node_attrs("b").unwrap(),
        &serde_json::json!({"color": "blue"})
    );
    assert!(!h.has_node("ghost")); // never auto-created
}

#[test]
fn set_edge_attributes_merges_skips_missing() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into()], vec![]),
        Some("e1".into()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    let mut heat = serde_json::Map::new();
    heat.insert("heat".to_string(), serde_json::json!(0.5));
    let mut x = serde_json::Map::new();
    x.insert("x".to_string(), serde_json::json!(1));
    h.set_edge_attributes(vec![("e1".to_string(), heat), ("ghost".to_string(), x)]);
    assert_eq!(
        h.edge_attrs("e1").unwrap(),
        &serde_json::json!({"w": 1, "heat": 0.5})
    );
    assert!(!h.has_edge("ghost"));
}

#[test]
fn clear_resets_everything_and_counter() {
    // D10: clear() ≡ new() — the uid counter resets (XGI continues it).
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge((vec!["a".into()], vec!["b".into()]), None, Value::Null)
        .unwrap();
    h.add_node("lonely", serde_json::json!({"x": 1}));
    h.set_graph_attr("name", serde_json::json!("test"));
    h.clear();
    assert_eq!(h.num_nodes(), 0);
    assert_eq!(h.num_edges(), 0);
    assert!(h.graph_attr("name").is_none());
    let auto = h
        .add_edge((vec!["z".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "0");
}

#[test]
fn clear_edges_keeps_nodes_and_counter() {
    // D16: XGI's DiHypergraph has NO clear_edges (AttributeError); the
    // core provides it for API uniformity — nodes, node attrs, and net
    // attrs survive; the counter continues (no "cleared ≡ fresh"
    // reading: the node state is preserved).
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge((vec!["a".into()], vec!["b".into()]), None, Value::Null)
        .unwrap();
    h.add_edge(
        (vec!["c".into()], vec![]),
        Some("e1".into()),
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.add_node("lonely", serde_json::json!({"x": 1}));
    h.set_graph_attr("name", serde_json::json!("test"));
    h.clear_edges();
    assert_eq!(h.num_edges(), 0);
    assert_eq!(h.num_nodes(), 4);
    assert_eq!(
        h.node_attrs("lonely").unwrap(),
        &serde_json::json!({"x": 1})
    );
    assert_eq!(h.graph_attr("name").unwrap(), &serde_json::json!("test"));
    assert!(h.memberships("a").unwrap().is_empty());
    let auto = h
        .add_edge((vec!["z".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "1");
}

#[test]
fn freeze_guards_all_structural_mutators() {
    // D12 uniform guard, incl. the two membership ops XGI's DiHypergraph
    // freeze list omits (extension, probed) and clear_edges (D16).
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    assert!(!h.is_frozen());
    h.freeze();
    assert!(h.is_frozen());
    let mut check = |f: &mut dyn FnMut(&mut DiHypergraph)| {
        let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| f(&mut h)));
        assert!(r.is_err());
    };
    check(&mut |h| {
        h.add_node("z", Value::Null);
    });
    check(&mut |h| {
        h.add_edge((vec!["a".into()], vec![]), None, Value::Null)
            .unwrap();
    });
    check(&mut |h| {
        h.add_edges_from(vec![(vec!["a".into()], vec![], None, Value::Null)]);
    });
    check(&mut |h| h.remove_node("a", false, true).unwrap());
    check(&mut |h| h.remove_edge("e1").unwrap());
    check(&mut |h| h.add_node_to_edge("e1", "n", Direction::In));
    check(&mut |h| {
        h.remove_node_from_edge("e1", "a", Direction::In, true)
            .unwrap();
    });
    check(&mut |h| h.clear());
    check(&mut |h| h.clear_edges());
    // Untouched by all of it.
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.tail("e1").unwrap(), vec!["a", "b"]);
}

#[test]
fn freeze_leaves_attr_channel_open() {
    // XGI parity: set_node_attributes / set_edge_attributes are NOT
    // guarded on a frozen network.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into()], vec![]),
        Some("e1".into()),
        serde_json::json!({}),
    )
    .unwrap();
    h.freeze();
    let mut k = serde_json::Map::new();
    k.insert("k".to_string(), serde_json::json!(1));
    h.set_node_attributes(vec![("a".to_string(), k.clone())]);
    h.set_edge_attributes(vec![("e1".to_string(), k)]);
    assert_eq!(h.node_attrs("a").unwrap()["k"], 1);
    assert_eq!(h.edge_attrs("e1").unwrap()["k"], 1);
}

#[test]
fn copy_is_independent_and_carries_counter_and_frozen() {
    // D13: the frozen flag carries (XGI's swizzled copy is not frozen).
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node("a", serde_json::json!({"color": "red"}));
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        None,
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.set_graph_attr("name", serde_json::json!("test"));
    h.freeze();

    let cp = h.copy();
    assert!(cp.is_frozen());

    // Mutate the original in every channel; the copy is untouched.
    h.node_attrs_mut("a").unwrap()["color"] = serde_json::json!("blue");
    h.edge_attrs_mut("0").unwrap()["heat"] = serde_json::json!(0.9);
    h.set_graph_attr("name", serde_json::json!("modified"));
    assert_eq!(cp.node_attrs("a").unwrap()["color"], "red");
    assert_eq!(cp.edge_attrs("0").unwrap()["heat"], 0.5);
    assert_eq!(cp.graph_attr("name").unwrap(), &serde_json::json!("test"));

    // Counter carried: an auto edge added to a fresh copy continues.
    let mut h2: DiHypergraph = DiHypergraph::new();
    h2.add_edge((vec!["a".into()], vec![]), None, Value::Null)
        .unwrap();
    let mut cp2 = h2.copy();
    let auto = cp2
        .add_edge((vec!["b".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "1");
}

#[test]
fn debug_formats_dimembers_in_insertion_order() {
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (
            vec!["a".into(), "b".into(), "c".into()],
            vec!["b".into(), "d".into()],
        ),
        None,
        Value::Null,
    )
    .unwrap();
    h.add_edge((vec!["a".into()], vec![]), Some("e1".into()), Value::Null)
        .unwrap();
    h.add_node("lonely", Value::Null); // never appears
    assert_eq!(
        format!("{h:?}"),
        "DiHypergraph([({a, b, c}, {b, d}), ({a}, {})])"
    );

    let empty: DiHypergraph = DiHypergraph::new();
    assert_eq!(format!("{empty:?}"), "DiHypergraph([])");

    let mut both_empty: DiHypergraph = DiHypergraph::new();
    both_empty
        .add_edge((vec![], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(format!("{both_empty:?}"), "DiHypergraph([({}, {})])");
}

#[test]
fn partial_eq_is_direction_aware() {
    let build = |tail: &[&str], head: &[&str]| {
        let mut h: DiHypergraph = DiHypergraph::new();
        h.add_edge(
            (
                tail.iter().map(|m| m.to_string()).collect(),
                head.iter().map(|m| m.to_string()).collect(),
            ),
            Some("e1".into()),
            Value::Null,
        )
        .unwrap();
        h
    };
    let a = build(&["a", "b"], &["c"]);
    assert_eq!(a, build(&["a", "b"], &["c"]));
    assert_ne!(a, build(&["c"], &["a", "b"])); // flipped -> not equal
    assert_eq!(a, build(&["b", "a"], &["c"])); // order insignificant
    assert_ne!(a, build(&["a", "b"], &["b"])); // head differs
                                               // Both-directions vs tail-only.
    assert_ne!(build(&["a", "b"], &["b"]), build(&["a", "b"], &[]));
}

#[test]
fn partial_eq_attrs_and_ids_significant() {
    let mut a: DiHypergraph = DiHypergraph::new();
    a.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e1".into()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    let mut b: DiHypergraph = DiHypergraph::new();
    b.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e1".into()),
        serde_json::json!({"w": 2}),
    )
    .unwrap();
    assert_ne!(a, b); // edge attrs
    let mut c: DiHypergraph = DiHypergraph::new();
    c.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e2".into()), // different id
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    assert_ne!(a, c);
    // Node attrs and net attrs significant.
    let mut d = a.copy();
    assert_eq!(a, d);
    *d.node_attrs_mut("a").unwrap() = serde_json::json!({"k": 1});
    assert_ne!(a, d);
    let mut e = a.copy();
    e.set_graph_attr("name", serde_json::json!("x"));
    assert_ne!(a, e);
}
