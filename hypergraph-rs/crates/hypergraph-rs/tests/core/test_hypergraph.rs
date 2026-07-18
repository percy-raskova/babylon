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
