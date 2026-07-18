//! Conformance replay: committed XGI ground-truth vectors
//! (`conformance/xgi_ground_truth.json`, generated from the installed XGI
//! runtime — never its docstrings — by `conformance/generate_fixtures.py`)
//! replayed against the Rust core.
//!
//! Every vector is either CONFORMANT (Rust asserts XGI's recorded outcome)
//! or a REGISTERED divergence (Dn — see the design spec's Divergence
//! Register), where the test asserts Rust's deliberate behavior AND pins
//! XGI's recorded truth, so drift on either side fails loudly. Regenerate
//! the fixture with `mise run rust:fixtures`; a fixture diff is news —
//! investigate before committing.

use hypergraph_rs::{EdgeError, Hypergraph};
use serde_json::Value;

fn ground_truth() -> Value {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/conformance/xgi_ground_truth.json"
    );
    let text = std::fs::read_to_string(path)
        .expect("conformance fixture missing — regenerate: mise run rust:fixtures");
    serde_json::from_str(&text).expect("conformance fixture is not valid JSON")
}

fn vector<'a>(gt: &'a Value, id: &str) -> &'a Value {
    &gt["vectors"][id]
}

/// XGI ids are typed (int auto-ids; arbitrary hashables for explicit ids);
/// the Rust core is stringly-typed at the ID boundary. Divergence D7.
fn id_str(v: &Value) -> String {
    match v {
        Value::Number(n) => n.to_string(),
        Value::String(s) => s.clone(),
        other => panic!("unexpected id type in fixture: {other}"),
    }
}

fn ids(v: &Value) -> Vec<String> {
    v.as_array().unwrap().iter().map(id_str).collect()
}

#[test]
fn fixture_is_pinned_to_xgi_0_10_2() {
    let gt = ground_truth();
    assert_eq!(gt["xgi_version"], "0.10.2");
    assert_eq!(gt["generated_by"], "conformance/generate_fixtures.py");
}

#[test]
fn conform_add_edge_empty_creates_edge() {
    // D1 RESOLVED: XGI's docstring claims XGIError on empty members; the
    // runtime creates an empty edge (and XGI's own test suite asserts it).
    // Rust matches the runtime.
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_empty_creates_edge");
    assert_eq!(v["num_edges"], 1);
    assert_eq!(v["num_nodes"], 0);

    let mut h: Hypergraph = Hypergraph::new();
    let id = h.add_edge(vec![], None, Value::Null).unwrap();
    assert_eq!(id, id_str(&v["edge_ids"][0]));
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.num_nodes(), 0);
    assert!(h.members(&id).unwrap().is_empty());
}

#[test]
fn conform_add_edge_three_empty_auto_ids() {
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_three_empty_auto_ids");
    let mut h: Hypergraph = Hypergraph::new();
    for expected in ids(&v["edge_ids"]) {
        assert_eq!(h.add_edge(vec![], None, Value::Null).unwrap(), expected);
    }
    assert_eq!(h.num_edges(), 3);
}

#[test]
fn conform_add_edge_auto_ids_sequence() {
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_auto_ids_sequence");
    let mut h: Hypergraph = Hypergraph::new();
    let a = h.add_edge(vec!["a".into()], None, Value::Null).unwrap();
    let b = h.add_edge(vec!["b".into()], None, Value::Null).unwrap();
    assert_eq!(vec![a, b], ids(&v["edge_ids"]));
}

#[test]
fn conform_add_edge_int_idx_bumps_counter() {
    // XGI with int idx 5 bumps the counter to 6. Rust is stringly-typed but
    // bumps for strings that parse as u64 — outcome-conformant.
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_int_idx_bumps_counter");
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into()], Some("5".into()), Value::Null)
        .unwrap();
    let auto = h.add_edge(vec!["b".into()], None, Value::Null).unwrap();
    assert_eq!(vec!["5".to_string(), auto], ids(&v["edge_ids"]));
}

#[test]
fn conform_add_edge_dedups_members() {
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_dedups_members");
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".into(), "a".into(), "b".into()],
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    assert_eq!(h.members("e1").unwrap(), vec!["a", "b"]);
}

#[test]
fn diverge_d2_dup_idx_errors_instead_of_warn_noop() {
    // D2: XGI warns + no-ops (returns None); the Rust core returns
    // Err(AlreadyExists). The PyO3 binding MUST translate back to
    // UserWarning + None for conformance. XGI's warning is pinned here.
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_dup_idx_warns_noop");
    assert_eq!(v["warned"], true);
    assert!(v["warning_prefix"]
        .as_str()
        .unwrap()
        .starts_with("uid e1 already exists"));

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into()], Some("e1".into()), Value::Null)
        .unwrap();
    let err = h.add_edge(vec!["b".into()], Some("e1".into()), Value::Null);
    assert!(matches!(err, Err(EdgeError::AlreadyExists { .. })));
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.members("e1").unwrap(), vec!["a"]);
}

#[test]
fn diverge_d3_str_numeric_idx_bumps_counter() {
    // D3: XGI does NOT bump its uid counter for a string idx ("5" → next
    // auto 0). Rust bumps iff `idx.parse::<u64>()` succeeds ("5" → "6").
    // Rationale: the ID boundary is stringly-typed (D7); XGI's int-idx
    // behavior is the common case worth preserving.
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_str_idx_no_bump");
    assert_eq!(ids(&v["edge_ids"]), vec!["5", "0"]); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into()], Some("5".into()), Value::Null)
        .unwrap();
    let auto = h.add_edge(vec!["b".into()], None, Value::Null).unwrap();
    assert_eq!(auto, "6"); // Rust divergence, deliberate
}

#[test]
fn diverge_d4_float_idx_does_not_bump() {
    // D4: XGI bumps for float idx 5.0 (float.is_integer()); Rust's
    // parse::<u64> rejects "5.0", so no bump — the D3 rule is exact.
    let gt = ground_truth();
    let v = vector(&gt, "add_edge_float_idx_bumps");
    assert_eq!(ids(&v["edge_ids"]), vec!["5.0", "6"]); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into()], Some("5.0".into()), Value::Null)
        .unwrap();
    let auto = h.add_edge(vec!["b".into()], None, Value::Null).unwrap();
    assert_eq!(auto, "0"); // Rust divergence, deliberate
}

#[test]
fn diverge_d6_add_node_replaces_instead_of_merging() {
    // D6: XGI merges attrs when re-adding an existing node ({x:1} then
    // {y:2} → {x:1, y:2}); the Rust core REPLACES (a generic N cannot
    // merge). The PyO3 binding merges dicts before calling to recover XGI
    // semantics.
    let gt = ground_truth();
    let v = vector(&gt, "add_node_existing_updates_attrs");
    assert_eq!(v["attrs"], serde_json::json!({"x": 1, "y": 2})); // XGI truth

    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::json!({"x": 1}));
    h.add_node("a", serde_json::json!({"y": 2}));
    assert_eq!(h.node_attrs("a").unwrap(), &serde_json::json!({"y": 2}));
    assert_eq!(h.num_nodes(), 1);
}

#[test]
fn conform_remove_edge_basic() {
    let gt = ground_truth();
    let v = vector(&gt, "remove_edge_basic");

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["a".into(), "c".into()], Some("e2".into()), Value::Null)
        .unwrap();
    h.remove_edge("e1").unwrap();

    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    // Nodes survive edge removal (XGI parity).
    let mut rust_nodes = h.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["node_ids"]));
    // Surviving edge keeps its members.
    let mut rust_members = h.members("e2").unwrap();
    rust_members.sort();
    assert_eq!(rust_members, ids(&v["members"]["e2"]));
    // Every surviving node's memberships reflect the removal.
    for (nid, expected) in v["memberships"].as_object().unwrap() {
        let mut got = h.memberships(nid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

#[test]
fn diverge_d2_remove_edge_missing_errors() {
    // Same error-channel class as D2: XGI signals a missing edge by raising
    // IDNotFound; the Rust core returns Err(EdgeError::NotFound) and the
    // PyO3 binding translates Err → raise. No new divergence number.
    let gt = ground_truth();
    let v = vector(&gt, "remove_edge_missing_raises");
    assert_eq!(v["exception"], "IDNotFound"); // XGI truth, pinned
    assert_eq!(v["message"], "'ID nonexistent not found'");

    let mut h: Hypergraph = Hypergraph::new();
    let err = h.remove_edge("nonexistent");
    assert!(matches!(err, Err(EdgeError::NotFound { .. })));
}
