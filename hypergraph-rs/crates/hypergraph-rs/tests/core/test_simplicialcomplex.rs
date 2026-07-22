//! Unit tests for `SimplicialComplex` — mirroring XGI's
//! `tests/core/test_simplicialcomplex.py`.

use hypergraph_rs::{EdgeError, SimplicialComplex};
use serde_json::Value;

#[test]
fn new_is_empty() {
    let s: SimplicialComplex = SimplicialComplex::new();
    assert_eq!(s.num_nodes(), 0);
    assert_eq!(s.num_edges(), 0);
    assert!(s.node_ids().is_empty());
    assert!(s.edge_ids().is_empty());
}

#[test]
fn add_simplex_creates_subface_closure() {
    // The top simplex takes the FIRST auto id; subfaces are EXACTLY the
    // proper non-empty subsets of sizes 2..n-1 (no singletons),
    // enumerated canonically: sizes n-1 down to 2, lexicographic by
    // member position (D5-class determinism; XGI shuffles via set()).
    let mut s: SimplicialComplex = SimplicialComplex::new();
    let top = s
        .add_simplex(vec!["1".into(), "2".into(), "3".into()], None, Value::Null)
        .unwrap();
    assert_eq!(top, "0", "the top simplex takes the first auto id");
    assert_eq!(s.num_edges(), 4);
    assert_eq!(s.members("0").unwrap(), vec!["1", "2", "3"]);
    // Canonical face ids: size 2 lexicographic — [1,2], [1,3], [2,3].
    assert_eq!(s.members("1").unwrap(), vec!["1", "2"]);
    assert_eq!(s.members("2").unwrap(), vec!["1", "3"]);
    assert_eq!(s.members("3").unwrap(), vec!["2", "3"]);
    // No singleton faces anywhere.
    for eid in s.edge_ids() {
        assert_ne!(s.members(&eid).unwrap().len(), 1);
    }
}

#[test]
fn add_simplex_four_simplex_has_sizes_two_and_three_only() {
    // 1 + C(4,3) + C(4,2) = 11 edges: the top, 4 size-3 faces, 6 size-2
    // faces — NO singletons (probed XGI behavior).
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(
        vec!["1".into(), "2".into(), "3".into(), "4".into()],
        None,
        Value::Null,
    )
    .unwrap();
    assert_eq!(s.num_edges(), 11);
    assert_eq!(s.members("0").unwrap(), vec!["1", "2", "3", "4"]);
    // Canonical order: size 3 first (ids 1..=4), then size 2 (5..=10).
    assert_eq!(s.members("1").unwrap(), vec!["1", "2", "3"]);
    assert_eq!(s.members("2").unwrap(), vec!["1", "2", "4"]);
    assert_eq!(s.members("3").unwrap(), vec!["1", "3", "4"]);
    assert_eq!(s.members("4").unwrap(), vec!["2", "3", "4"]);
    assert_eq!(s.members("5").unwrap(), vec!["1", "2"]);
    assert_eq!(s.members("6").unwrap(), vec!["1", "3"]);
    assert_eq!(s.members("7").unwrap(), vec!["1", "4"]);
    assert_eq!(s.members("8").unwrap(), vec!["2", "3"]);
    assert_eq!(s.members("9").unwrap(), vec!["2", "4"]);
    assert_eq!(s.members("10").unwrap(), vec!["3", "4"]);
}

#[test]
fn add_simplex_two_members_adds_no_subfaces() {
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(vec!["1".into(), "2".into()], None, Value::Null)
        .unwrap();
    assert_eq!(s.num_edges(), 1);
    assert_eq!(s.members("0").unwrap(), vec!["1", "2"]);
}

#[test]
fn add_simplex_dedups_members() {
    // XGI casts members to a frozenset; the closure runs on the SET.
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(
        vec!["1".into(), "1".into(), "2".into(), "3".into()],
        None,
        Value::Null,
    )
    .unwrap();
    assert_eq!(s.num_edges(), 4);
    assert_eq!(s.members("0").unwrap(), vec!["1", "2", "3"]);
}

#[test]
fn redundant_add_returns_existing_id_silently() {
    // Member-set dedup precedes the idx check (probed): a reordered
    // re-add is a silent no-op; even a NEW explicit idx on an existing
    // member set is discarded (NOT consumed). XGI returns None both
    // ways; the core returns Ok(id of the EXISTING edge) — D8 class.
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(vec!["1".into(), "2".into(), "3".into()], None, Value::Null)
        .unwrap();
    assert_eq!(s.num_edges(), 4);

    let again = s
        .add_simplex(vec!["3".into(), "2".into(), "1".into()], None, Value::Null)
        .unwrap();
    assert_eq!(again, "0", "redundant add returns the existing id");
    assert_eq!(s.num_edges(), 4);

    let again2 = s
        .add_simplex(
            vec!["3".into(), "2".into(), "1".into()],
            Some("newid".into()),
            Value::Null,
        )
        .unwrap();
    assert_eq!(again2, "0");
    assert!(
        !s.edge_ids().contains(&"newid".to_string()),
        "the idx is not consumed"
    );
    assert_eq!(s.num_edges(), 4);

    // Adding an existing FACE is likewise a silent no-op.
    let face = s
        .add_simplex(vec!["2".into(), "1".into()], None, Value::Null)
        .unwrap();
    assert_eq!(face, "1");
    assert_eq!(s.num_edges(), 4);
}

#[test]
fn dup_idx_with_different_members_errors() {
    // D2-class: XGI warns + no-ops; the core returns Err(AlreadyExists).
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(
        vec!["1".into(), "2".into(), "3".into()],
        Some("s1".into()),
        Value::Null,
    )
    .unwrap();
    let err = s.add_simplex(vec!["4".into(), "5".into()], Some("s1".into()), Value::Null);
    assert!(matches!(err, Err(EdgeError::AlreadyExists { .. })));
    assert!(!s.node_ids().contains(&"4".to_string()));
    assert_eq!(s.num_edges(), 4);
}

#[test]
fn empty_simplex_is_created() {
    // D1-class docstring lie: XGI's Notes claim empty simplices cannot
    // be added; the runtime CREATES an empty simplex (probed). A second
    // empty add is a silent no-op returning the existing id.
    let mut s: SimplicialComplex = SimplicialComplex::new();
    let id = s.add_simplex(vec![], None, Value::Null).unwrap();
    assert_eq!(id, "0");
    assert_eq!(s.num_edges(), 1);
    assert_eq!(s.num_nodes(), 0);
    assert!(s.members("0").unwrap().is_empty());
    assert!(s.has_simplex(&[]));
    let again = s.add_simplex(vec![], None, Value::Null).unwrap();
    assert_eq!(again, "0");
    assert_eq!(s.num_edges(), 1);
}

#[test]
fn attrs_land_only_on_the_top_simplex() {
    // Probed: subfaces get the empty attr dict (XGI {} ≈ the core's
    // Null placeholder, D7-class convention).
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(
        vec!["1".into(), "2".into(), "3".into()],
        None,
        serde_json::json!({"color": "red"}),
    )
    .unwrap();
    assert_eq!(
        s.edge_attrs("0").unwrap(),
        &serde_json::json!({"color": "red"})
    );
    for eid in ["1", "2", "3"] {
        assert_eq!(s.edge_attrs(eid).unwrap(), &Value::Null);
    }
}

#[test]
fn uid_counter_rules_match_the_core() {
    // Auto ids sequence; explicit numeric str idx bumps (D3 rule);
    // non-numeric idx does not — faces consume the auto sequence.
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(
        vec!["1".into(), "2".into(), "3".into()],
        Some("10".into()),
        Value::Null,
    )
    .unwrap();
    // "10" parses as u64 -> bump: faces take 11, 12, 13.
    assert_eq!(s.edge_ids(), vec!["10", "11", "12", "13"]);

    let mut s2: SimplicialComplex = SimplicialComplex::new();
    s2.add_simplex(
        vec!["1".into(), "2".into(), "3".into()],
        Some("top".into()),
        Value::Null,
    )
    .unwrap();
    // "top" does not parse -> no bump: faces take 0, 1, 2.
    assert_eq!(s2.edge_ids(), vec!["top", "0", "1", "2"]);
}

#[test]
fn falsy_idx_is_explicit_in_rust() {
    // D17: XGI's add_simplex treats a FALSY idx (0, "") as auto; the
    // core's Option<String> is exact — Some("0") is explicit.
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(
        vec!["1".into(), "2".into(), "3".into()],
        Some("5".into()),
        Value::Null,
    )
    .unwrap();
    let id = s
        .add_simplex(vec!["4".into(), "5".into()], Some("0".into()), Value::Null)
        .unwrap();
    assert_eq!(id, "0", "Some(\"0\") is an explicit id, not auto");
    assert_eq!(s.members("0").unwrap(), vec!["4", "5"]);
}

#[test]
fn has_simplex_is_member_set_comparison() {
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(vec!["1".into(), "2".into()], None, Value::Null)
        .unwrap();
    s.add_simplex(vec!["2".into(), "3".into(), "4".into()], None, Value::Null)
        .unwrap();
    assert!(s.has_simplex(&["2".to_string(), "1".to_string()])); // reordered
    assert!(s.has_simplex(&["2".to_string(), "3".into(), "4".into()])); // top
    assert!(s.has_simplex(&["2".to_string(), "3".to_string()])); // closure face
    assert!(!s.has_simplex(&["1".to_string(), "3".to_string()])); // missing set
    assert!(!s.has_simplex(&["2".to_string()])); // no singletons
    assert!(!s.has_simplex(&[])); // no empty simplex here
}

#[test]
fn queries_delegate_to_the_inner_hypergraph() {
    let mut s: SimplicialComplex = SimplicialComplex::new();
    s.add_simplex(
        vec!["a".into(), "b".into(), "c".into()],
        Some("top".into()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    s.set_graph_attr("name", serde_json::json!("test"));
    assert_eq!(s.num_nodes(), 3);
    assert_eq!(s.num_edges(), 4);
    assert_eq!(s.node_ids(), vec!["a", "b", "c"]);
    assert_eq!(s.edge_ids(), vec!["top", "0", "1", "2"]);
    assert_eq!(s.members("top").unwrap(), vec!["a", "b", "c"]);
    assert_eq!(s.memberships("a").unwrap(), vec!["top", "0", "1"]);
    assert_eq!(s.edge_attrs("top").unwrap()["w"], 1);
    assert_eq!(s.graph_attr("name").unwrap(), &serde_json::json!("test"));
    // Node attrs are readable; auto-created nodes carry the Null default.
    assert_eq!(s.node_attrs("a").unwrap(), &Value::Null);
}

#[test]
fn missing_id_queries_return_none() {
    let s: SimplicialComplex = SimplicialComplex::new();
    assert!(s.members("ghost").is_none());
    assert!(s.memberships("ghost").is_none());
    assert!(s.node_attrs("ghost").is_none());
    assert!(s.edge_attrs("ghost").is_none());
    assert!(s.graph_attr("ghost").is_none());
}
