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
