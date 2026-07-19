use hypergraph_rs::Hypergraph;

#[test]
fn test_add_node_creates_new_node() {
    let mut h: Hypergraph = Hypergraph::new();
    let created = h.add_node("a", serde_json::Value::Null);
    assert!(created);
    assert_eq!(h.num_nodes(), 1);
    assert!(h.has_node("a"));
}

#[test]
fn test_add_node_returns_false_for_existing() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::Value::Null);
    let created = h.add_node("a", serde_json::Value::Null);
    assert!(!created);
    assert_eq!(h.num_nodes(), 1);
}

#[test]
fn test_has_node_returns_false_for_missing() {
    let h: Hypergraph = Hypergraph::new();
    assert!(!h.has_node("nonexistent"));
}

#[test]
fn test_num_nodes_starts_at_zero() {
    let h: Hypergraph = Hypergraph::new();
    assert_eq!(h.num_nodes(), 0);
}

use hypergraph_rs::EdgeError;

#[test]
fn test_add_edge_with_explicit_idx() {
    let mut h: Hypergraph = Hypergraph::new();
    let edge_id = h
        .add_edge(
            vec!["a".to_string(), "b".to_string(), "c".to_string()],
            Some("myedge".to_string()),
            serde_json::Value::Null,
        )
        .unwrap();
    assert_eq!(edge_id, "myedge");
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.num_nodes(), 3);
}

#[test]
fn test_add_edge_auto_generates_id() {
    let mut h: Hypergraph = Hypergraph::new();
    let id1 = h
        .add_edge(
            vec!["a".to_string(), "b".to_string()],
            None,
            serde_json::Value::Null,
        )
        .unwrap();
    assert_eq!(id1, "0");
    let id2 = h
        .add_edge(
            vec!["c".to_string(), "d".to_string()],
            None,
            serde_json::Value::Null,
        )
        .unwrap();
    assert_eq!(id2, "1");
}

#[test]
fn test_add_edge_duplicate_idx_returns_error() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    let result = h.add_edge(
        vec!["b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    );
    assert!(matches!(result, Err(EdgeError::AlreadyExists { .. })));
    assert_eq!(h.num_edges(), 1);
}

#[test]
fn test_add_edge_deduplicates_members() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    assert_eq!(h.num_nodes(), 2);
}

#[test]
fn test_add_edge_empty_members_creates_empty_edge() {
    // XGI v0.10.2 ground truth (verified against the runtime, not the
    // docstring — the docstring claims XGIError, the behavior creates an
    // empty edge; XGI's own test_add_edge asserts sizes {0: 0, 1: 0, 2: 0}).
    // The conformance gate is behavioral. Divergence register D1.
    let mut h: Hypergraph = Hypergraph::new();
    let id = h.add_edge(vec![], None, serde_json::Value::Null).unwrap();
    assert_eq!(id, "0");
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.num_nodes(), 0);
    assert!(h.members(&id).unwrap().is_empty());
}

#[test]
fn test_add_edge_three_empty_edges_get_auto_ids() {
    let mut h: Hypergraph = Hypergraph::new();
    for expected in ["0", "1", "2"] {
        let id = h.add_edge(vec![], None, serde_json::Value::Null).unwrap();
        assert_eq!(id, expected);
    }
    assert_eq!(h.num_edges(), 3);
}

#[test]
fn test_add_edge_auto_id_after_explicit_idx() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("5".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    let next = h
        .add_edge(vec!["b".to_string()], None, serde_json::Value::Null)
        .unwrap();
    assert_eq!(next, "6");
}

#[test]
fn test_has_edge_returns_true_for_existing() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    assert!(h.has_edge("e1"));
}

#[test]
fn test_has_edge_returns_false_for_missing() {
    let h: Hypergraph = Hypergraph::new();
    assert!(!h.has_edge("nonexistent"));
}

#[test]
fn test_num_edges_counts_correctly() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["b".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["c".to_string()],
        Some("e3".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    assert_eq!(h.num_edges(), 3);
}

#[test]
fn test_memberships_returns_edge_ids() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["a".to_string(), "c".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    let mships = h.memberships("a").unwrap();
    assert_eq!(mships.len(), 2);
    assert!(mships.contains(&"e1".to_string()));
    assert!(mships.contains(&"e2".to_string()));
}

#[test]
fn test_memberships_returns_empty_for_isolate() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("lonely", serde_json::Value::Null);
    assert!(h.memberships("lonely").unwrap().is_empty());
}

#[test]
fn test_memberships_returns_none_for_missing() {
    let h: Hypergraph = Hypergraph::new();
    assert!(h.memberships("nonexistent").is_none());
}

#[test]
fn test_members_returns_node_ids() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    let members = h.members("e1").unwrap();
    assert_eq!(members.len(), 3);
    assert!(members.contains(&"a".to_string()));
}

#[test]
fn test_members_returns_none_for_missing() {
    let h: Hypergraph = Hypergraph::new();
    assert!(h.members("nonexistent").is_none());
}

#[test]
fn test_node_ids_insertion_order() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("c", serde_json::Value::Null);
    h.add_node("a", serde_json::Value::Null);
    h.add_node("b", serde_json::Value::Null);
    assert_eq!(h.node_ids(), vec!["c", "a", "b"]);
}

#[test]
fn test_edge_ids_insertion_order() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["x".to_string()],
        Some("e3".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["x".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["x".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    assert_eq!(h.edge_ids(), vec!["e3", "e1", "e2"]);
}

#[test]
fn test_node_ids_empty() {
    let h: Hypergraph = Hypergraph::new();
    assert!(h.node_ids().is_empty());
}

#[test]
fn test_members_insertion_order() {
    // III.7 parity: member iteration is insertion-ordered, not petgraph's
    // LIFO neighbor order. Divergence register D5 (XGI returns unordered
    // sets; we are strictly more defined).
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec![
            "a".to_string(),
            "b".to_string(),
            "c".to_string(),
            "d".to_string(),
        ],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    assert_eq!(h.members("e1").unwrap(), vec!["a", "b", "c", "d"]);
}

#[test]
fn test_memberships_insertion_order() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "x".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["a".to_string(), "y".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["a".to_string(), "z".to_string()],
        Some("e3".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    assert_eq!(h.memberships("a").unwrap(), vec!["e1", "e2", "e3"]);
}

#[test]
fn test_add_node_existing_replaces_attrs() {
    // XGI: "If node is already in the hypergraph, its attributes are still
    // updated." Core semantics replace (a generic N cannot merge; the PyO3
    // layer merges dicts before calling). Divergence D6.
    let mut h: Hypergraph = Hypergraph::new();
    assert!(h.add_node("a", serde_json::json!({"x": 1})));
    assert!(!h.add_node("a", serde_json::json!({"y": 2})));
    assert_eq!(h.node_attrs("a").unwrap(), &serde_json::json!({"y": 2}));
    assert_eq!(h.num_nodes(), 1);
}

#[test]
fn test_node_attrs_missing_returns_none() {
    let h: Hypergraph = Hypergraph::new();
    assert!(h.node_attrs("nonexistent").is_none());
}

#[test]
fn test_edge_attrs_read() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"w": 5}),
    )
    .unwrap();
    assert_eq!(h.edge_attrs("e1").unwrap(), &serde_json::json!({"w": 5}));
    assert!(h.edge_attrs("nope").is_none());
}

#[test]
fn test_graph_attrs_roundtrip() {
    // XGI parity: H.graph dict.
    let mut h: Hypergraph = Hypergraph::new();
    assert!(h.graph_attr("name").is_none());
    h.set_graph_attr("name", serde_json::json!("myhypergraph"));
    assert_eq!(
        h.graph_attr("name").unwrap(),
        &serde_json::json!("myhypergraph")
    );
}

#[test]
fn test_node_attrs_mut() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::json!({"count": 0}));
    {
        let attrs = h.node_attrs_mut("a").unwrap();
        attrs["count"] = serde_json::json!(5);
    }
    assert_eq!(h.node_attrs("a").unwrap()["count"], 5);
}

#[test]
fn test_edge_attrs_mut() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"heat": 0.3}),
    )
    .unwrap();
    {
        let attrs = h.edge_attrs_mut("e1").unwrap();
        attrs["heat"] = serde_json::json!(0.9);
    }
    assert_eq!(h.edge_attrs("e1").unwrap()["heat"], 0.9);
}

#[test]
fn test_edge_attrs_missing_returns_none() {
    let h: Hypergraph = Hypergraph::new();
    assert!(h.edge_attrs("nonexistent").is_none());
}

#[test]
fn test_graph_attr_overwrite() {
    let mut h: Hypergraph = Hypergraph::new();
    h.set_graph_attr("tick", serde_json::json!(1));
    h.set_graph_attr("tick", serde_json::json!(99));
    assert_eq!(h.graph_attr("tick"), Some(&serde_json::json!(99)));
}

#[test]
fn test_clear_removes_everything() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.add_node("lonely", serde_json::json!({"x": 1}));
    h.set_graph_attr("name", serde_json::json!("test"));
    h.clear();
    assert_eq!(h.num_nodes(), 0);
    assert_eq!(h.num_edges(), 0);
    assert!(h.node_ids().is_empty());
    assert!(h.edge_ids().is_empty());
    assert!(h.graph_attr("name").is_none());
}

#[test]
fn test_remove_edge_basic() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_edge("e1").unwrap();
    assert!(!h.has_edge("e1"));
    assert_eq!(h.num_edges(), 0);
    assert!(h.has_node("a"));
    assert!(h.has_node("b"));
    assert!(h.memberships("a").unwrap().is_empty());
}

#[test]
fn test_remove_edge_missing_returns_error() {
    let mut h: Hypergraph = Hypergraph::new();
    let result = h.remove_edge("nonexistent");
    assert!(matches!(result, Err(EdgeError::NotFound { .. })));
}

#[test]
fn test_remove_edge_preserves_other_edges() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["a".to_string(), "c".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_edge("e1").unwrap();
    assert!(!h.has_edge("e1"));
    assert!(h.has_edge("e2"));
    assert_eq!(h.memberships("a").unwrap(), vec!["e2"]);
}

#[test]
fn test_remove_edge_preserves_insertion_order() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["a".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["a".to_string()],
        Some("e3".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_edge("e2").unwrap();
    assert_eq!(h.edge_ids(), vec!["e1", "e3"]);
}

use hypergraph_rs::NodeError;

#[test]
fn test_remove_node_weak_removes_from_edges() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_node("b", false).unwrap();
    assert!(!h.has_node("b"));
    assert!(h.has_edge("e1"));
    let members = h.members("e1").unwrap();
    assert!(!members.contains(&"b".to_string()));
    assert!(members.contains(&"a".to_string()));
}

#[test]
fn test_remove_node_weak_removes_singleton_edges() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_node("a", false).unwrap();
    assert!(!h.has_node("a"));
    assert!(!h.has_edge("e1"));
}

#[test]
fn test_remove_node_strong_removes_all_containing_edges() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["a".to_string(), "c".to_string(), "d".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_node("a", true).unwrap();
    assert!(!h.has_node("a"));
    assert!(!h.has_edge("e1"));
    assert!(!h.has_edge("e2"));
    assert!(h.has_node("b"));
    assert!(h.has_node("c"));
}

#[test]
fn test_remove_node_missing_returns_error() {
    let mut h: Hypergraph = Hypergraph::new();
    let result = h.remove_node("nonexistent", false);
    assert!(matches!(result, Err(NodeError::NotFound { .. })));
}

#[test]
fn test_remove_node_preserves_insertion_order() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::Value::Null);
    h.add_node("b", serde_json::Value::Null);
    h.add_node("c", serde_json::Value::Null);
    h.remove_node("b", false).unwrap();
    assert_eq!(h.node_ids(), vec!["a", "c"]);
}

#[test]
fn test_copy_produces_independent_clone() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.set_graph_attr("name", serde_json::json!("test"));

    let mut h2 = h.copy();
    assert_eq!(h2.num_nodes(), 2);
    assert_eq!(h2.num_edges(), 1);
    assert_eq!(h2.edge_attrs("e1").unwrap()["heat"], 0.5);

    h2.add_node("c", serde_json::Value::Null);
    h2.set_graph_attr("name", serde_json::json!("modified"));
    assert_eq!(h.num_nodes(), 2);
    assert!(!h.has_node("c"));
    assert_eq!(h.graph_attr("name"), Some(&serde_json::json!("test")));
}

#[test]
fn test_copy_of_empty() {
    let h: Hypergraph = Hypergraph::new();
    let h2 = h.copy();
    assert_eq!(h2.num_nodes(), 0);
    assert_eq!(h2.num_edges(), 0);
}

#[test]
fn test_add_nodes_from_bulk() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_nodes_from(vec![
        ("a".to_string(), serde_json::json!({"x": 1})),
        ("b".to_string(), serde_json::json!({"x": 2})),
    ]);
    assert_eq!(h.num_nodes(), 2);
    assert_eq!(h.node_attrs("a").unwrap()["x"], 1);
}

#[test]
fn test_add_edges_from_bulk() {
    let mut h: Hypergraph = Hypergraph::new();
    let results = h.add_edges_from(vec![
        (
            vec!["a".to_string(), "b".to_string()],
            Some("e1".to_string()),
            serde_json::json!({"w": 1}),
        ),
        (
            vec!["b".to_string(), "c".to_string()],
            None,
            serde_json::Value::Null,
        ),
    ]);
    assert_eq!(results.len(), 2);
    assert!(results.iter().all(|r| r.is_ok()));
    assert_eq!(h.num_edges(), 2);
    assert_eq!(h.num_nodes(), 3);
    assert_eq!(h.edge_ids(), vec!["e1", "0"]);
}

#[test]
fn test_add_edges_from_with_duplicate_idx() {
    let mut h: Hypergraph = Hypergraph::new();
    let results = h.add_edges_from(vec![
        (
            vec!["a".to_string()],
            Some("e1".to_string()),
            serde_json::Value::Null,
        ),
        (
            vec!["b".to_string()],
            Some("e1".to_string()),
            serde_json::Value::Null,
        ),
    ]);
    assert!(results[0].is_ok());
    assert!(results[1].is_err());
    assert_eq!(h.num_edges(), 1);
}

#[test]
fn test_eq_same_structure() {
    let mut h1: Hypergraph = Hypergraph::new();
    h1.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    let mut h2: Hypergraph = Hypergraph::new();
    h2.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    assert_eq!(h1, h2);
}

#[test]
fn test_eq_different_edge_attrs() {
    let mut h1: Hypergraph = Hypergraph::new();
    h1.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    let mut h2: Hypergraph = Hypergraph::new();
    h2.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"w": 2}),
    )
    .unwrap();
    assert_ne!(h1, h2);
}

#[test]
fn test_eq_different_members() {
    let mut h1: Hypergraph = Hypergraph::new();
    h1.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    let mut h2: Hypergraph = Hypergraph::new();
    h2.add_edge(
        vec!["a".to_string(), "c".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    assert_ne!(h1, h2);
}

#[test]
fn test_eq_both_empty() {
    let h1: Hypergraph = Hypergraph::new();
    let h2: Hypergraph = Hypergraph::new();
    assert_eq!(h1, h2);
}

#[test]
fn test_add_node_to_edge_existing_edge() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_node_to_edge("e1", "c");
    let members = h.members("e1").unwrap();
    assert!(members.contains(&"c".to_string()));
    assert_eq!(members.len(), 3);
}

#[test]
fn test_add_node_to_edge_auto_creates_edge_and_node() {
    let mut h: Hypergraph = Hypergraph::new();
    // Neither edge "new_edge" nor node "new_node" exist
    h.add_node_to_edge("new_edge", "new_node");
    assert!(h.has_edge("new_edge"));
    assert!(h.has_node("new_node"));
    let members = h.members("new_edge").unwrap();
    assert_eq!(members, vec!["new_node"]);
}

#[test]
fn test_add_node_to_edge_is_infallible() {
    // Phase 2 Task 1: add_node_to_edge returns () — XGI auto-creates a
    // missing edge AND a missing node and has no error path (probed:
    // returns None in every branch, idempotent on re-add). The vestigial
    // Result<(), EdgeError> is gone.
    let mut h: Hypergraph = Hypergraph::new();
    let _: () = h.add_node_to_edge("e1", "c");
    assert_eq!(h.members("e1").unwrap(), vec!["c"]);
}

#[test]
fn test_remove_node_from_edge_basic() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_node_from_edge("e1", "b", true).unwrap();
    let members = h.members("e1").unwrap();
    assert!(!members.contains(&"b".to_string()));
    assert_eq!(members.len(), 2);
    // Node b still exists (just not in e1 anymore)
    assert!(h.has_node("b"));
}

#[test]
fn test_remove_node_from_edge_removes_empty_edge() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_node_from_edge("e1", "a", true).unwrap();
    // e1 was a singleton, now empty — should be removed
    assert!(!h.has_edge("e1"));
    assert!(h.has_node("a"));
}

#[test]
fn test_remove_node_from_edge_keep_empty() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.remove_node_from_edge("e1", "a", false).unwrap();
    // remove_empty=false: edge stays (now empty)
    assert!(h.has_edge("e1"));
    assert!(h.members("e1").unwrap().is_empty());
}

use hypergraph_rs::MembershipError;

#[test]
fn test_remove_node_from_edge_missing_edge_returns_error() {
    // MembershipError::EdgeNotFound — XGI raises XGIError ("Edge e1 not in
    // the hypergraph"); the core's variant is discriminative without
    // string-matching (Phase 2 Task 1; the binding translates Err -> raise,
    // D2 channel class).
    let mut h: Hypergraph = Hypergraph::new();
    let err = h.remove_node_from_edge("e1", "a", true).unwrap_err();
    assert_eq!(
        err,
        MembershipError::EdgeNotFound {
            edge_id: "e1".to_string()
        }
    );
    assert_eq!(format!("{err}"), "edge e1 does not exist");
}

#[test]
fn test_remove_node_from_edge_missing_node_returns_error() {
    // MembershipError::NodeNotFound — the edge exists, the node does not
    // (XGI: "Node ghost not in the hypergraph").
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    let err = h.remove_node_from_edge("e1", "ghost", true).unwrap_err();
    assert_eq!(
        err,
        MembershipError::NodeNotFound {
            node_id: "ghost".to_string()
        }
    );
    assert_eq!(format!("{err}"), "node ghost does not exist");
}

#[test]
fn test_remove_node_from_edge_node_not_in_edge_returns_error() {
    // MembershipError::NotAMember — both exist, but the node is not in the
    // edge (XGI: "Edge e1 does not contain node b").
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_node("b", serde_json::Value::Null);
    let err = h.remove_node_from_edge("e1", "b", true).unwrap_err();
    assert_eq!(
        err,
        MembershipError::NotAMember {
            node_id: "b".to_string(),
            edge_id: "e1".to_string()
        }
    );
    assert_eq!(format!("{err}"), "node b is not a member of edge e1");
}

#[test]
fn test_set_node_attributes_from_pairs() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::Value::Null);
    h.add_node("b", serde_json::Value::Null);

    let mut attrs_a = serde_json::Map::new();
    attrs_a.insert("color".to_string(), serde_json::json!("red"));
    let mut attrs_b = serde_json::Map::new();
    attrs_b.insert("color".to_string(), serde_json::json!("blue"));

    h.set_node_attributes(vec![("a".to_string(), attrs_a), ("b".to_string(), attrs_b)]);

    assert_eq!(h.node_attrs("a").unwrap()["color"], "red");
    assert_eq!(h.node_attrs("b").unwrap()["color"], "blue");
}

#[test]
fn test_set_node_attributes_skips_missing() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::Value::Null);

    let mut attrs = serde_json::Map::new();
    attrs.insert("x".to_string(), serde_json::json!(1));

    h.set_node_attributes(vec![
        ("a".to_string(), attrs.clone()),
        ("nonexistent".to_string(), attrs),
    ]);

    // "a" got the attribute, "nonexistent" was silently skipped
    assert_eq!(h.node_attrs("a").unwrap()["x"], 1);
    assert!(!h.has_node("nonexistent"));
}

#[test]
fn test_set_edge_attributes_from_pairs() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["b".to_string()],
        Some("e2".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();

    let mut attrs_e1 = serde_json::Map::new();
    attrs_e1.insert("weight".to_string(), serde_json::json!(5));
    let mut attrs_e2 = serde_json::Map::new();
    attrs_e2.insert("weight".to_string(), serde_json::json!(10));

    h.set_edge_attributes(vec![
        ("e1".to_string(), attrs_e1),
        ("e2".to_string(), attrs_e2),
    ]);

    assert_eq!(h.edge_attrs("e1").unwrap()["weight"], 5);
    assert_eq!(h.edge_attrs("e2").unwrap()["weight"], 10);
}

#[test]
fn test_clear_edges_keeps_nodes() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    h.add_node("lonely", serde_json::json!({"x": 1}));
    h.clear_edges();
    assert_eq!(h.num_nodes(), 3); // a, b, lonely all kept
    assert_eq!(h.num_edges(), 0);
    // Node attrs preserved
    assert_eq!(h.node_attrs("lonely").unwrap()["x"], 1);
    // No memberships
    assert!(h.memberships("a").unwrap().is_empty());
}

#[test]
fn test_clear_edges_continues_uid_counter() {
    // XGI parity (conformance vector clear_edges_keeps_nodes_counter):
    // unlike clear() (D10 reset), clear_edges does NOT reset the auto-id
    // counter — the node state survives, so counter continuity matches
    // state continuity.
    let mut h: Hypergraph = Hypergraph::new();
    let first = h
        .add_edge(vec!["a".to_string()], None, serde_json::Value::Null)
        .unwrap();
    assert_eq!(first, "0");
    h.clear_edges();
    let next = h
        .add_edge(vec!["z".to_string()], None, serde_json::Value::Null)
        .unwrap();
    assert_eq!(next, "1");
}

#[test]
fn test_freeze_prevents_mutation() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::Value::Null);
    h.freeze();
    assert!(h.is_frozen());
    // Mutation should panic
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let mut h = h;
        h.add_node("b", serde_json::Value::Null);
    }));
    assert!(result.is_err(), "add_node should panic when frozen");
}

#[test]
fn test_is_frozen_false_by_default() {
    let h: Hypergraph = Hypergraph::new();
    assert!(!h.is_frozen());
}

#[test]
fn test_freeze_guards_all_structural_mutators() {
    // XGI parity for the shared set (add_node, add_edge, remove_node,
    // remove_edge, add_node_to_edge, remove_node_from_edge, clear) plus
    // D12: the Rust core ALSO guards clear_edges, which XGI's freeze
    // monkey-patch list omits. Guards fire before any mutation, so one
    // frozen graph serves every probe.
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string()],
        Some("e1".to_string()),
        serde_json::Value::Null,
    )
    .unwrap();
    h.freeze();
    let mut panics = |f: &mut dyn FnMut(&mut Hypergraph)| {
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| f(&mut h))).is_err()
    };
    assert!(panics(&mut |h| {
        h.add_node("z", serde_json::Value::Null);
    }));
    assert!(panics(&mut |h| {
        h.add_nodes_from(vec![("z".to_string(), serde_json::Value::Null)]);
    }));
    assert!(panics(&mut |h| {
        h.add_edge(vec!["a".to_string()], None, serde_json::Value::Null)
            .unwrap();
    }));
    assert!(panics(&mut |h| {
        h.add_edges_from(vec![(
            vec!["a".to_string()],
            Some("e2".to_string()),
            serde_json::Value::Null,
        )]);
    }));
    assert!(panics(&mut |h| h.remove_node("a", false).unwrap()));
    assert!(panics(&mut |h| h.remove_edge("e1").unwrap()));
    assert!(panics(&mut |h| h.add_node_to_edge("e1", "c")));
    assert!(panics(&mut |h| h
        .remove_node_from_edge("e1", "a", true)
        .unwrap()));
    assert!(panics(&mut |h| h.clear()));
    assert!(panics(&mut |h| h.clear_edges()));
    // Nothing mutated through the guards.
    assert_eq!(h.num_nodes(), 2);
    assert_eq!(h.num_edges(), 1);
}

#[test]
fn test_freeze_leaves_attr_channel_open() {
    // XGI parity: freeze guards STRUCTURAL mutation only. XGI leaves
    // set_node_attributes / set_edge_attributes / net-attr set / private
    // attr-dict writes unguarded on frozen networks; the Rust core
    // matches (node_attrs_mut / edge_attrs_mut cannot be guarded — they
    // return &mut; same hole shape as XGI's private-dict access).
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string()],
        Some("e1".to_string()),
        serde_json::json!({}),
    )
    .unwrap();
    h.freeze();
    let mut attrs = serde_json::Map::new();
    attrs.insert("k".to_string(), serde_json::json!(1));
    h.set_node_attributes(vec![("a".to_string(), attrs.clone())]);
    h.set_edge_attributes(vec![("e1".to_string(), attrs)]);
    h.set_graph_attr("name", serde_json::json!("x"));
    assert_eq!(h.node_attrs("a").unwrap()["k"], 1);
    assert_eq!(h.edge_attrs("e1").unwrap()["k"], 1);
    assert_eq!(h.graph_attr("name"), Some(&serde_json::json!("x")));
}

#[test]
fn test_copy_of_frozen_is_frozen() {
    // Divergence D13: XGI's copy() of a frozen network is NOT frozen
    // (freeze is per-instance method-swizzling; the fresh instance never
    // gets the patch). The Rust core's frozen flag is data — copy()
    // carries it.
    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::Value::Null);
    h.freeze();
    let cp = h.copy();
    assert!(cp.is_frozen());
}

#[test]
fn test_debug_format_matches_xgi_repr() {
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
        None,
        serde_json::Value::Null,
    )
    .unwrap();
    h.add_edge(
        vec!["b".to_string(), "c".to_string()],
        None,
        serde_json::Value::Null,
    )
    .unwrap();
    let repr = format!("{:?}", h);
    // XGI __repr__ returns: Hypergraph([{a, b, c}, {b, c}])
    // Our Debug should include the class name and edge members
    assert!(repr.contains("Hypergraph"));
    assert!(repr.contains("a"));
    assert!(repr.contains("b"));
    assert!(repr.contains("c"));
    // Exact format: XGI parity shape, edges and members insertion-ordered
    // (divergence D5 — deterministic where XGI's sets are unordered).
    assert_eq!(repr, "Hypergraph([{a, b, c}, {b, c}])");
}

#[test]
fn test_debug_format_empty() {
    let h: Hypergraph = Hypergraph::new();
    let repr = format!("{:?}", h);
    assert!(repr.contains("Hypergraph"));
    assert_eq!(repr, "Hypergraph([])");
}

#[test]
fn test_debug_format_empty_edge_and_lonely_node() {
    // An empty edge formats as "{}" (XGI's Python-set artifact "set()" is
    // not reproduced — same D5 class); a lonely node never appears (XGI
    // parity — the repr lists only edges' members).
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec![], None, serde_json::Value::Null).unwrap();
    h.add_node("lonely", serde_json::Value::Null);
    assert_eq!(format!("{:?}", h), "Hypergraph([{}])");
}
