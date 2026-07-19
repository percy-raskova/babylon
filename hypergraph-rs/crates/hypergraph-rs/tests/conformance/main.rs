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

use hypergraph_rs::{DiHypergraph, Direction, EdgeError, Hypergraph, MembershipError, NodeError};
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
fn conform_node_attr_set_read() {
    // XGI-facing mutation: H.nodes["a"]["color"] = "red" mutates the node's
    // attr dict in place. The Rust core exposes the same write path via
    // node_attrs_mut; reading it back matches XGI's recorded dict.
    let gt = ground_truth();
    let v = vector(&gt, "node_attr_set_read");
    assert_eq!(v["attrs"], serde_json::json!({"color": "red"})); // XGI truth

    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::json!({}));
    h.node_attrs_mut("a").unwrap()["color"] = serde_json::json!("red");
    assert_eq!(h.node_attrs("a").unwrap(), &v["attrs"]);
}

#[test]
fn diverge_d10_clear_resets_uid_counter() {
    // XGI's clear() (remove_net_attr=True default) empties all nodes, edges,
    // node/edge attrs, and net attrs — the Rust core conforms on all of
    // that. D10: XGI does NOT reset its auto-id counter (the next auto id
    // continues at 1); the Rust core resets edge_uid_counter, so a cleared
    // hypergraph behaves identically to a fresh one (clear() ≡ new();
    // III.7 replay-from-empty determinism).
    let gt = ground_truth();
    let v = vector(&gt, "clear_all");
    assert_eq!(v["num_nodes"], 0); // XGI truth, pinned
    assert_eq!(v["num_edges"], 0);
    assert_eq!(v["node_ids"], serde_json::json!([]));
    assert_eq!(v["edge_ids"], serde_json::json!([]));
    assert_eq!(v["net_attrs"], serde_json::json!({}));
    assert_eq!(ids(&v["auto_ids_after_clear"]), vec!["1"]); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], None, Value::Null)
        .unwrap();
    h.add_edge(
        vec!["c".into(), "d".into()],
        Some("e1".into()),
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
    assert!(h.node_attrs("lonely").is_none());
    assert!(h.edge_attrs("e1").is_none());

    // D10: Rust resets the counter — the post-clear auto id is "0", not "1".
    let auto = h.add_edge(vec!["z".into()], None, Value::Null).unwrap();
    assert_eq!(auto, "0"); // Rust divergence, deliberate
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

#[test]
fn conform_remove_node_weak() {
    // Weak removal (XGI defaults strong=False, remove_empty=True): the node
    // is dropped from every containing edge; an edge it leaves EMPTY is
    // removed (e3 was the singleton ["b"]). Other nodes and edges survive.
    let gt = ground_truth();
    let v = vector(&gt, "remove_node_weak");

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".into(), "b".into(), "c".into()],
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(vec!["b".into(), "d".into()], Some("e2".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["b".into()], Some("e3".into()), Value::Null)
        .unwrap();
    h.remove_node("b", false, true).unwrap();

    assert_eq!(h.edge_ids(), ids(&v["edge_ids"])); // e3 emptied -> removed
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    let mut rust_nodes = h.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["node_ids"]));
    for (eid, expected) in v["members"].as_object().unwrap() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
    for (nid, expected) in v["memberships"].as_object().unwrap() {
        let mut got = h.memberships(nid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

#[test]
fn conform_remove_node_strong() {
    // Strong removal: EVERY edge containing the node is removed (e1, e2);
    // edges not containing it survive (e4), as do the other nodes.
    let gt = ground_truth();
    let v = vector(&gt, "remove_node_strong");

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(
        vec!["a".into(), "c".into(), "d".into()],
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(vec!["c".into(), "d".into()], Some("e4".into()), Value::Null)
        .unwrap();
    h.remove_node("a", true, true).unwrap();

    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    let mut rust_nodes = h.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["node_ids"]));
    for (eid, expected) in v["members"].as_object().unwrap() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
    for (nid, expected) in v["memberships"].as_object().unwrap() {
        let mut got = h.memberships(nid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

#[test]
fn diverge_d2_remove_node_missing_errors() {
    // Same error-channel class as D2: XGI signals a missing node by raising
    // IDNotFound; the Rust core returns Err(NodeError::NotFound) and the
    // PyO3 binding translates Err → raise. No new divergence number.
    let gt = ground_truth();
    let v = vector(&gt, "remove_node_missing_raises");
    assert_eq!(v["exception"], "IDNotFound"); // XGI truth, pinned
    assert_eq!(v["message"], "'ID nonexistent not found'");

    let mut h: Hypergraph = Hypergraph::new();
    let err = h.remove_node("nonexistent", false, true);
    assert!(matches!(err, Err(NodeError::NotFound { .. })));
}

#[test]
fn conform_remove_node_remove_empty() {
    // XGI's remove_node(n, strong, remove_empty) is three-mode (register
    // D9, implemented in Phase 2 Task 2): weak + remove_empty=False leaves
    // the emptied edge in place (queryable: members(e) == []); weak +
    // remove_empty=True (the XGI default) drops it; strong removes every
    // incident edge REGARDLESS of the flag. The Rust core conforms on all
    // three modes.
    let gt = ground_truth();
    let v = vector(&gt, "remove_node_remove_empty");
    assert_eq!(v["weak_keep"]["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["weak_keep"]["has_node_b"], false); // XGI truth, pinned
    assert_eq!(v["weak_keep"]["members"]["e2"], serde_json::json!([])); // pinned

    // Weak + remove_empty=False: the emptied edge SURVIVES.
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["b".into()], Some("e2".into()), Value::Null)
        .unwrap();
    h.remove_node("b", false, false).unwrap();
    assert_eq!(h.edge_ids(), ids(&v["weak_keep"]["edge_ids"]));
    assert_eq!(
        h.num_edges(),
        v["weak_keep"]["num_edges"].as_u64().unwrap() as usize
    );
    assert!(!h.has_node("b"));
    assert_eq!(h.node_ids(), ids(&v["weak_keep"]["node_ids"]));
    assert_eq!(h.members("e1").unwrap(), vec!["a"]);
    assert_eq!(h.members("e2").unwrap(), Vec::<String>::new()); // emptied, alive

    // Weak + remove_empty=True: the emptied edge is dropped.
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["b".into()], Some("e2".into()), Value::Null)
        .unwrap();
    h.remove_node("b", false, true).unwrap();
    assert_eq!(h.edge_ids(), ids(&v["weak_drop"]["edge_ids"]));
    assert_eq!(
        h.num_edges(),
        v["weak_drop"]["num_edges"].as_u64().unwrap() as usize
    );

    // Strong + remove_empty=False: incident edges are removed ANYWAY.
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(
        vec!["a".into(), "c".into(), "d".into()],
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(vec!["c".into(), "d".into()], Some("e4".into()), Value::Null)
        .unwrap();
    h.remove_node("a", true, false).unwrap();
    assert_eq!(h.edge_ids(), ids(&v["strong_ignores_flag"]["edge_ids"]));
    assert_eq!(h.node_ids(), ids(&v["strong_ignores_flag"]["node_ids"]));
    assert_eq!(h.members("e4").unwrap(), vec!["c", "d"]);
}

#[test]
fn diverge_d2_remove_nodes_from_missing_warns_per_item() {
    // XGI's remove_nodes_from WARNS on a missing id ("Node ghost not in
    // hypergraph" — note: no "the", unlike remove_node's IDNotFound
    // message), SKIPS it, and CONTINUES with the rest; returns None.
    // D2-class channel translation: the Rust core records a per-item
    // Err(NodeError::NotFound) in the returned Vec and continues; the
    // binding warns per Err item to reproduce XGI's behavior.
    let gt = ground_truth();
    let v = vector(&gt, "remove_nodes_from_missing");
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["warned"], true); // XGI truth, pinned
    assert_eq!(v["warning_message"], "Node ghost not in hypergraph"); // pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["b".into(), "c".into()], Some("e2".into()), Value::Null)
        .unwrap();
    let results = h.remove_nodes_from(
        vec!["b".to_string(), "ghost".to_string(), "c".to_string()],
        false,
        true,
    );
    assert_eq!(results.len(), 3);
    assert!(results[0].is_ok());
    assert_eq!(
        results[1],
        Err(NodeError::NotFound {
            node_id: "ghost".to_string()
        })
    );
    assert!(results[2].is_ok(), "continues past the missing id");

    assert_eq!(h.node_ids(), ids(&v["node_ids"]));
    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.members("e1").unwrap(), vec!["a"]);
}

#[test]
fn diverge_d2_remove_edges_from_missing_stops_after_err() {
    // XGI's remove_edges_from RAISES IDNotFound("ID ghost not found") on
    // the first missing id — ids BEFORE it are already removed (partial
    // effects); ids AFTER it are never attempted (["e1", "ghost", "e3"]
    // leaves e2 AND e3 in place). D2-class channel translation: the Rust
    // core records per-item results and STOPS after the first Err (the
    // returned Vec has one entry per ATTEMPTED id, length <= input), so
    // the binding can reproduce the raise exactly — the state already
    // matches XGI's post-raise state.
    let gt = ground_truth();
    let v = vector(&gt, "remove_edges_from_missing");
    assert_eq!(v["exception"], "IDNotFound"); // XGI truth, pinned
    assert_eq!(v["message"], "'ID ghost not found'"); // XGI truth, pinned
    assert_eq!(v["all_valid_return"], Value::Null); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["b".into(), "c".into()], Some("e2".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["c".into(), "d".into()], Some("e3".into()), Value::Null)
        .unwrap();
    let results = h.remove_edges_from(vec![
        "e1".to_string(),
        "ghost".to_string(),
        "e3".to_string(),
    ]);
    assert_eq!(results.len(), 2, "e3 was never attempted");
    assert!(results[0].is_ok());
    assert_eq!(
        results[1],
        Err(EdgeError::NotFound {
            edge_id: "ghost".to_string()
        })
    );
    assert_eq!(h.edge_ids(), ids(&v["edge_ids_after"])); // e2 AND e3 survive
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);

    // All-valid bunch: every listed edge removed, nodes survive.
    let mut h2: Hypergraph = Hypergraph::new();
    h2.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h2.add_edge(vec!["b".into(), "c".into()], Some("e2".into()), Value::Null)
        .unwrap();
    let results = h2.remove_edges_from(vec!["e1".to_string(), "e2".to_string()]);
    assert_eq!(results.len(), 2);
    assert!(results.iter().all(|r| r.is_ok()));
    assert!(h2.edge_ids().is_empty());
    assert_eq!(h2.node_ids(), ids(&v["all_valid_nodes"]));
}

#[test]
fn conform_remove_edge_then_readd() {
    // Reviewer insurance: removing an edge must not leave residue. A re-added
    // idx gets FRESH members (a/b do not resurrect into "e1"), and XGI's uid
    // counter does not reuse the removed id — string idx "e1" never bumped
    // the counter, so the next auto id is 0 (recorded as int in the fixture).
    let gt = ground_truth();
    let v = vector(&gt, "remove_edge_then_readd");
    assert_eq!(v["return"], Value::Null); // XGI add_edge returns None, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.remove_edge("e1").unwrap();
    h.add_edge(vec!["c".into()], Some("e1".into()), Value::Null)
        .unwrap();
    let auto = h.add_edge(vec!["d".into()], None, Value::Null).unwrap();

    // Fresh members for the re-added idx — no resurrection of a/b.
    assert_eq!(h.members("e1").unwrap(), vec!["c"]);
    assert_eq!(auto, "0");
    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    let mut rust_nodes = h.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["node_ids"]));
    for (eid, expected) in v["members"].as_object().unwrap() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

#[test]
fn conform_copy_independence() {
    // XGI's H.copy() is a DEEP, independent clone: mutating the original in
    // any channel (node attrs, edge attrs, net attrs, membership) leaves
    // the copy untouched. The Rust core conforms — clone() is deep on every
    // channel (serde_json::Value attrs clone by value).
    let gt = ground_truth();
    let v = vector(&gt, "copy_independence");

    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::json!({"color": "red"}));
    h.add_edge(
        vec!["a".into(), "b".into()],
        Some("e1".into()),
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.set_graph_attr("name", serde_json::json!("test"));

    let c = h.copy();

    // Mutate the original in every channel.
    h.node_attrs_mut("a").unwrap()["color"] = serde_json::json!("blue");
    h.edge_attrs_mut("e1").unwrap()["heat"] = serde_json::json!(0.9);
    h.set_graph_attr("name", serde_json::json!("modified"));
    h.add_node("c", Value::Null);

    // The copy is untouched — XGI's recorded truth.
    assert_eq!(c.node_attrs("a").unwrap(), &v["node_attrs"]);
    assert_eq!(c.edge_attrs("e1").unwrap(), &v["edge_attrs"]);
    assert_eq!(c.graph_attr("name"), Some(&v["net_name"]));
    assert_eq!(c.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    assert_eq!(c.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(c.has_node("c"), v["has_c"].as_bool().unwrap());
}

#[test]
fn conform_eq_structural() {
    // XGI's Hypergraph.__eq__ delegates to xgi.algorithms.equal with the
    // defaults (compare_edge_ids=True, compare_attrs=True): edge-id ->
    // members mapping, node attrs, edge attrs, and net attrs are all
    // significant; insertion/member order is not. The Rust core's PartialEq
    // matches every recorded verdict.
    let gt = ground_truth();
    let v = vector(&gt, "eq_structural");
    // XGI truth, pinned.
    assert_eq!(v["same"], true);
    assert_eq!(v["diff_edge_attr"], false);
    assert_eq!(v["diff_members"], false);
    assert_eq!(v["diff_edge_id"], false);
    assert_eq!(v["diff_net_attr"], false);
    assert_eq!(v["member_order_insignificant"], true);
    assert_eq!(v["lonely_same"], true);
    assert_eq!(v["diff_node_attr"], false);

    let build = |members: &[&str],
                 idx: &str,
                 edge_attr: Value,
                 solo: Option<(&str, Value)>,
                 net: Option<(&str, Value)>| {
        let mut h: Hypergraph = Hypergraph::new();
        h.add_edge(
            members.iter().map(|m| m.to_string()).collect(),
            Some(idx.into()),
            edge_attr,
        )
        .unwrap();
        if let Some((n, attrs)) = solo {
            h.add_node(n, attrs);
        }
        if let Some((k, val)) = net {
            h.set_graph_attr(k, val);
        }
        h
    };
    let a = build(&["a", "b"], "e1", serde_json::json!({"w": 1}), None, None);
    assert_eq!(
        a,
        build(&["a", "b"], "e1", serde_json::json!({"w": 1}), None, None)
    );
    assert_ne!(
        a,
        build(&["a", "b"], "e1", serde_json::json!({"w": 2}), None, None)
    );
    assert_ne!(a, build(&["a", "c"], "e1", Value::Null, None, None));
    assert_ne!(a, build(&["a", "b"], "e2", Value::Null, None, None));
    assert_ne!(
        a,
        build(
            &["a", "b"],
            "e1",
            serde_json::json!({"w": 1}),
            None,
            Some(("name", serde_json::json!("x")))
        )
    );
    assert_eq!(
        a,
        build(&["b", "a"], "e1", serde_json::json!({"w": 1}), None, None)
    );
    let l1 = build(
        &[],
        "e1",
        Value::Null,
        Some(("solo", serde_json::json!({"color": "red"}))),
        None,
    );
    let l2 = build(
        &[],
        "e1",
        Value::Null,
        Some(("solo", serde_json::json!({"color": "red"}))),
        None,
    );
    let l3 = build(
        &[],
        "e1",
        Value::Null,
        Some(("solo", serde_json::json!({"color": "blue"}))),
        None,
    );
    assert_eq!(l1, l2);
    assert_ne!(l1, l3);
}

#[test]
fn conform_copy_counter_preserved() {
    // Reviewer insurance (S3-1): XGI's copy() carries the auto-id counter
    // (`cp._edge_uid = copy(self._edge_uid)`) — an auto edge added to the
    // copy gets the NEXT counter value, it does not restart at 0. The Rust
    // core conforms: copy() clones edge_uid_counter.
    let gt = ground_truth();
    let v = vector(&gt, "copy_counter_preserved");
    assert_eq!(ids(&v["h_edge_ids"]), vec!["0"]); // XGI truth, pinned
    assert_eq!(ids(&v["cp_edge_ids"]), vec!["0", "1"]); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    assert_eq!(
        h.add_edge(vec!["a".into()], None, Value::Null).unwrap(),
        "0"
    );
    let mut cp = h.copy();
    let auto = cp.add_edge(vec!["b".into()], None, Value::Null).unwrap();
    assert_eq!(auto, "1");
    assert_eq!(h.edge_ids(), ids(&v["h_edge_ids"]));
    assert_eq!(cp.edge_ids(), ids(&v["cp_edge_ids"]));
    assert_eq!(h.num_edges(), v["h_num_edges"].as_u64().unwrap() as usize);
    assert_eq!(cp.num_edges(), v["cp_num_edges"].as_u64().unwrap() as usize);
}

#[test]
fn conform_add_node_to_edge_autocreate() {
    // XGI's add_node_to_edge auto-creates a missing edge AND a missing node
    // (runtime-verified), returns None, is idempotent on re-add (set
    // semantics), and preserves existing edge attrs. The Rust core conforms
    // on every channel.
    let gt = ground_truth();
    let v = vector(&gt, "add_node_to_edge_autocreate");
    assert_eq!(v["return_create"], Value::Null); // XGI truth, pinned
    assert_eq!(v["return_readd"], Value::Null); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_node_to_edge("new_edge", "new_node"); // both missing
    h.add_edge(
        vec!["a".into(), "b".into()],
        Some("e1".into()),
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.add_node_to_edge("e1", "c"); // existing edge, new node
    h.add_node_to_edge("e1", "c"); // idempotent re-add
    h.add_node_to_edge("e1", "a"); // existing node into existing edge

    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    let mut rust_nodes = h.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["node_ids"]));
    for (eid, expected) in v["members"].as_object().unwrap() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
    for (nid, expected) in v["memberships"].as_object().unwrap() {
        let mut got = h.memberships(nid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
    assert_eq!(h.edge_attrs("e1").unwrap(), &v["edge_attrs_e1"]);
}

#[test]
fn diverge_d11_add_node_to_edge_numeric_bumps_counter() {
    // D11: XGI's add_node_to_edge NEVER touches _edge_uid — auto-creating a
    // numeric edge id does not bump the counter, so the next auto id is 0
    // (and XGI's add_edge does not existence-check its auto id: the same
    // sequence with id 0 silently OVERWRITES that edge's members in XGI).
    // The Rust core bumps iff `edge_id.parse::<u64>()` succeeds — the D3
    // rule extended to this method — foreclosing the collision class.
    let gt = ground_truth();
    let v = vector(&gt, "add_node_to_edge_numeric_id_no_bump");
    assert_eq!(ids(&v["edge_ids"]), vec!["5", "0"]); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_node_to_edge("5", "x");
    let auto = h.add_edge(vec!["y".into()], None, Value::Null).unwrap();
    assert_eq!(auto, "6"); // Rust divergence, deliberate
    assert_eq!(h.members("5").unwrap(), vec!["x"]);
    assert_eq!(h.members("6").unwrap(), vec!["y"]);
}

#[test]
fn conform_remove_node_from_edge_keep_empty() {
    // remove_empty=False: the emptied edge SURVIVES (empty member set);
    // the node survives too. The Rust core conforms.
    let gt = ground_truth();
    let v = vector(&gt, "remove_node_from_edge_keep_empty");
    assert_eq!(ids(&v["edge_ids"]), vec!["e1"]); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.remove_node_from_edge("e1", "a", false).unwrap();

    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    assert!(h.has_node("a"));
    for (eid, expected) in v["members"].as_object().unwrap() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
    for (nid, expected) in v["memberships"].as_object().unwrap() {
        let mut got = h.memberships(nid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

#[test]
fn conform_remove_node_from_edge_drop_empty() {
    // remove_empty=True (the XGI default): an edge left empty is removed;
    // the node survives (still a member of e1). The Rust core conforms.
    let gt = ground_truth();
    let v = vector(&gt, "remove_node_from_edge_drop_empty");
    assert_eq!(ids(&v["edge_ids"]), vec!["e1"]); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_edge(vec!["b".into()], Some("e2".into()), Value::Null)
        .unwrap();
    h.remove_node_from_edge("e2", "b", true).unwrap();

    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    let mut rust_nodes = h.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["node_ids"]));
    for (eid, expected) in v["members"].as_object().unwrap() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
    for (nid, expected) in v["memberships"].as_object().unwrap() {
        let mut got = h.memberships(nid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

#[test]
fn conform_membership_errors() {
    // XGI raises XGIError on all three remove_node_from_edge failure
    // branches, each with a DISTINCT message (pinned below). The Rust core
    // maps each branch to a dedicated MembershipError variant
    // (EdgeNotFound / NodeNotFound / NotAMember) so callers can
    // discriminate without string-matching; the PyO3 binding translates
    // Err -> raise, reproducing XGI's exact messages (D2 error-channel
    // class — no new divergence number).
    let gt = ground_truth();
    let v = vector(&gt, "membership_errors");
    assert_eq!(v["missing_edge"]["exception"], "XGIError"); // XGI truth, pinned
    assert_eq!(
        v["missing_edge"]["message"],
        "Edge noedge not in the hypergraph"
    );
    assert_eq!(v["missing_node"]["exception"], "XGIError"); // XGI truth, pinned
    assert_eq!(
        v["missing_node"]["message"],
        "Node ghost not in the hypergraph"
    );
    assert_eq!(v["not_in_edge"]["exception"], "XGIError"); // XGI truth, pinned
    assert_eq!(
        v["not_in_edge"]["message"],
        "Edge e1 does not contain node b"
    );

    let mut h: Hypergraph = Hypergraph::new();
    let err = h.remove_node_from_edge("noedge", "a", true);
    assert_eq!(
        err,
        Err(MembershipError::EdgeNotFound {
            edge_id: "noedge".to_string()
        })
    );

    let mut h2: Hypergraph = Hypergraph::new();
    h2.add_edge(vec!["a".into()], Some("e1".into()), Value::Null)
        .unwrap();
    let err = h2.remove_node_from_edge("e1", "ghost", true);
    assert_eq!(
        err,
        Err(MembershipError::NodeNotFound {
            node_id: "ghost".to_string()
        })
    );

    let mut h3: Hypergraph = Hypergraph::new();
    h3.add_edge(vec!["a".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h3.add_node("b", Value::Null);
    let err = h3.remove_node_from_edge("e1", "b", true);
    assert_eq!(
        err,
        Err(MembershipError::NotAMember {
            node_id: "b".to_string(),
            edge_id: "e1".to_string()
        })
    );
}

#[test]
fn conform_set_node_attributes_bulk() {
    // XGI's set_node_attributes(values, name=None) takes a dict-of-dicts:
    // it MERGES into each existing node's attr dict, and a missing node is
    // warned about ("Node ghost does not exist!") + SKIPPED — never
    // auto-created, never raises. A list-of-pairs input raises XGIError at
    // the Python boundary (XGI is dict-of-dicts only; the Rust core takes
    // pairs and the binding converts — D7 class). The warn channel is a
    // binding concern (the core never warns — D2 channel class); the core
    // is outcome-conformant on every recorded channel.
    let gt = ground_truth();
    let v = vector(&gt, "set_node_attributes_bulk");
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["warned"], true); // XGI truth, pinned
    assert_eq!(v["warning_message"], "Node ghost does not exist!");
    assert_eq!(v["pairs_exception"], "XGIError"); // XGI truth, pinned
    assert_eq!(v["pairs_message"], "Must pass a dictionary of dictionaries");
    assert_eq!(v["attrs_a"], serde_json::json!({"x": 1, "color": "red"})); // merge

    let mut h: Hypergraph = Hypergraph::new();
    h.add_node("a", serde_json::json!({"x": 1}));
    h.add_node("b", serde_json::json!({}));
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

    // Existing nodes MERGED; ghost silently skipped, never auto-created.
    assert_eq!(h.node_attrs("a").unwrap(), &v["attrs_a"]);
    assert_eq!(h.node_attrs("b").unwrap(), &v["attrs_b"]);
    assert!(!h.has_node("ghost"));
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
}

#[test]
fn conform_set_edge_attributes_bulk() {
    // Edge twin of the above: merge into existing edge attr dicts; a
    // missing edge id warns ("Edge ghost does not exist!") + skips; edge
    // count and membership untouched. The Rust core conforms on outcome.
    let gt = ground_truth();
    let v = vector(&gt, "set_edge_attributes_bulk");
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["warned"], true); // XGI truth, pinned
    assert_eq!(v["warning_message"], "Edge ghost does not exist!");
    assert_eq!(v["attrs_e1"], serde_json::json!({"w": 1, "heat": 0.5})); // merge

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".into()],
        Some("e1".into()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    h.add_edge(vec!["b".into()], Some("e2".into()), serde_json::json!({}))
        .unwrap();
    let mut heat = serde_json::Map::new();
    heat.insert("heat".to_string(), serde_json::json!(0.5));
    let mut x = serde_json::Map::new();
    x.insert("x".to_string(), serde_json::json!(1));
    h.set_edge_attributes(vec![("e1".to_string(), heat), ("ghost".to_string(), x)]);

    assert_eq!(h.edge_attrs("e1").unwrap(), &v["attrs_e1"]);
    assert_eq!(h.edge_attrs("e2").unwrap(), &v["attrs_e2"]);
    assert!(!h.has_edge("ghost"));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
}

#[test]
fn conform_clear_edges_keeps_nodes_counter() {
    // XGI's clear_edges(): "Remove all edges from the graph without
    // altering any nodes." Nodes, node attrs, and net attrs survive;
    // memberships empty; returns None. Like clear() (D10) it does NOT
    // reset the uid counter — but unlike D10 there is no "cleared ≡
    // fresh" reading (the node state is preserved), so counter continuity
    // matches state continuity and the Rust core CONFORMS: no reset.
    let gt = ground_truth();
    let v = vector(&gt, "clear_edges_keeps_nodes_counter");
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(ids(&v["auto_ids_after_clear_edges"]), vec!["1"]); // XGI truth

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], None, Value::Null)
        .unwrap();
    h.add_edge(
        vec!["c".into(), "d".into()],
        Some("e1".into()),
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.add_node("lonely", serde_json::json!({"x": 1}));
    h.set_graph_attr("name", serde_json::json!("test"));
    h.clear_edges();

    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    assert_eq!(h.num_edges(), 0);
    let mut rust_nodes = h.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["node_ids"]));
    assert_eq!(h.node_attrs("lonely").unwrap(), &v["lonely_attrs"]);
    assert_eq!(
        h.graph_attr("name"),
        Some(&v["net_attrs"]["name"]),
        "net attrs survive clear_edges"
    );
    assert!(h.memberships("a").unwrap().is_empty());
    assert!(h.edge_ids().is_empty());

    // CONFORM (no D-number): the counter continues — next auto id "1".
    let auto = h.add_edge(vec!["z".into()], None, Value::Null).unwrap();
    assert_eq!(auto, "1");
    assert_eq!(vec![auto], ids(&v["auto_ids_after_clear_edges"]));
}

#[test]
fn conform_freeze_blocks_mutation() {
    // XGI's freeze() guards add_node(s)_from, remove_node(s)_from,
    // add_edge(s)_from, remove_edge(s)_from, add_node_to_edge,
    // remove_node_from_edge, and clear by monkey-patching each with a
    // raiser (`XGIError: Frozen higher-order network can't be modified`);
    // is_frozen reads the `frozen` attribute. The Rust core panics on the
    // same structural mutators (panic ≡ raise at the core; the binding
    // converts — D2 error-channel class). XGI leaves the attr-dict
    // channel OPEN on frozen networks (set_node_attributes /
    // set_edge_attributes / net-attr set / private-dict writes all
    // unguarded) — the Rust core matches: no guard on the attr setters
    // (and node_attrs_mut/edge_attrs_mut cannot be guarded — they return
    // &mut; same hole shape as XGI's private-dict access).
    let gt = ground_truth();
    let v = vector(&gt, "freeze_blocks_mutation");
    assert_eq!(v["is_frozen_before"], false); // XGI truth, pinned
    assert_eq!(v["is_frozen_after"], true); // XGI truth, pinned
    for method in [
        "add_node",
        "add_edge",
        "remove_node",
        "remove_edge",
        "add_node_to_edge",
        "remove_node_from_edge",
        "clear",
    ] {
        assert_eq!(v["guarded"][method]["exception"], "XGIError"); // pinned
        assert_eq!(
            v["guarded"][method]["message"],
            "Frozen higher-order network can't be modified"
        );
    }
    // The attr-dict channel is NOT guarded in XGI — pinned as truth.
    assert_eq!(v["guarded"]["set_node_attributes"], Value::Null);
    assert_eq!(v["guarded"]["set_edge_attributes"], Value::Null);

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(
        vec!["a".into(), "b".into()],
        Some("e1".into()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    assert!(!h.is_frozen());
    h.freeze();
    assert!(h.is_frozen());

    // Every XGI-guarded structural mutator panics in the Rust core. The
    // guards fire before any mutation, so one frozen graph serves every
    // probe.
    let mut panics = |f: &mut dyn FnMut(&mut Hypergraph)| {
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| f(&mut h))).is_err()
    };
    assert!(panics(&mut |h| {
        h.add_node("z", Value::Null);
    }));
    assert!(panics(&mut |h| {
        h.add_edge(vec!["a".into()], None, Value::Null).unwrap();
    }));
    assert!(panics(&mut |h| h.remove_node("a", false, true).unwrap()));
    assert!(panics(&mut |h| h.remove_edge("e1").unwrap()));
    assert!(panics(&mut |h| h.add_node_to_edge("e1", "c")));
    assert!(panics(&mut |h| h
        .remove_node_from_edge("e1", "a", true)
        .unwrap()));
    assert!(panics(&mut |h| h.clear()));

    // XGI parity: the attr-dict channel stays OPEN on a frozen graph.
    let mut attrs = serde_json::Map::new();
    attrs.insert("k".to_string(), serde_json::json!(1));
    h.set_node_attributes(vec![("a".to_string(), attrs.clone())]);
    h.set_edge_attributes(vec![("e1".to_string(), attrs)]);
    assert_eq!(h.node_attrs("a").unwrap()["k"], 1);
    assert_eq!(h.edge_attrs("e1").unwrap()["k"], 1);
}

#[test]
fn diverge_d12_freeze_guards_clear_edges() {
    // D12: XGI's freeze monkey-patch list omits clear_edges — a FROZEN
    // XGI network can still have every edge deleted (probed live:
    // guarded["clear_edges"] is None = no raise). XGI's omission is an
    // artifact of freeze-by-method-swizzling, not a designed semantic; a
    // freeze that permits wholesale edge deletion is not a freeze. The
    // Rust core's frozen flag guards ALL structural mutators uniformly,
    // clear_edges included.
    let gt = ground_truth();
    let v = vector(&gt, "freeze_blocks_mutation");
    assert_eq!(v["guarded"]["clear_edges"], Value::Null); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.freeze();
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| h.clear_edges()));
    assert!(
        result.is_err(),
        "Rust divergence: clear_edges panics when frozen"
    );
    // The panic fired BEFORE any mutation: the original is untouched.
    assert_eq!(h.num_edges(), 1);
}

#[test]
fn diverge_d13_copy_carries_frozen() {
    // D13: XGI's freeze is per-instance method-swizzling — copy() builds a
    // fresh instance that never gets the patch, so a copy of a frozen XGI
    // network is NOT frozen (an implementation artifact, not semantics).
    // The Rust core's frozen flag is data; copy() is a deep clone of data
    // and carries it — a clone that silently drops immutability is a
    // footgun the core declines to reproduce.
    let gt = ground_truth();
    let v = vector(&gt, "freeze_blocks_mutation");
    assert_eq!(v["copy_of_frozen_is_frozen"], false); // XGI truth, pinned

    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.freeze();
    let cp = h.copy();
    assert!(cp.is_frozen(), "Rust divergence: copy of frozen is frozen");
}

#[test]
fn diverge_d2_add_edges_from_dup_errors_continues() {
    // XGI's add_edges_from warns + skips a duplicate idx and CONTINUES with
    // the rest (["b"]/"e1" dropped — its member "b" is never added; ["c"]/
    // "e2" kept). Same D2 error-channel class: the Rust core surfaces the
    // dup as Err(AlreadyExists) in the per-edge Vec<Result> and still
    // continues — no new divergence number. The PyO3 binding translates
    // Err → UserWarning + skip for conformance.
    let gt = ground_truth();
    let v = vector(&gt, "add_edges_from_dup_warns_continues");
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["warned"], true); // XGI truth, pinned
    assert!(v["warning_prefix"]
        .as_str()
        .unwrap()
        .starts_with("uid e1 already exists"));

    let mut h: Hypergraph = Hypergraph::new();
    let results = h.add_edges_from(vec![
        (vec!["a".into()], Some("e1".into()), Value::Null),
        (vec!["b".into()], Some("e1".into()), Value::Null),
        (vec!["c".into()], Some("e2".into()), Value::Null),
    ]);
    assert_eq!(results.len(), 3);
    assert!(results[0].is_ok());
    assert!(matches!(results[1], Err(EdgeError::AlreadyExists { .. })));
    assert!(results[2].is_ok());

    // Dup skipped, the rest kept — XGI's recorded final state.
    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_edges(), v["num_edges"].as_u64().unwrap() as usize);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    for (eid, expected) in v["members"].as_object().unwrap() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

#[test]
fn conform_repr_format() {
    // XGI's __repr__ is f"{cls}({self.edges.members()})" — the class name
    // wrapping the edge-members list. The Rust core's Debug produces the
    // same SHAPE (Hypergraph([{...}, ...])) with members in INSERTION
    // order — cited divergence D5 (XGI's member sets are unordered; their
    // repr order is hash-randomized across runs, so the fixture records
    // members SORTED and the stable projections only). Rust is strictly
    // more defined: deterministic where XGI is set-ordered. No new
    // D-number — the D5 row's "strictly more defined" rationale covers
    // the repr surface, including rendering an empty edge as "{}" where
    // Python must say "set()".
    let gt = ground_truth();
    let v = vector(&gt, "repr_format");
    assert_eq!(v["repr_prefix"], "Hypergraph("); // XGI truth, pinned
    assert_eq!(v["repr_empty"], "Hypergraph([])"); // XGI truth, pinned
    assert_eq!(v["repr_lone_empty_edge"], "Hypergraph([set()])"); // pinned
    assert_eq!(
        v["members_sorted"],
        serde_json::json!([["a", "b", "c"], ["b", "c"]])
    ); // XGI truth (sorted), pinned

    // Same graph in Rust: members format insertion-ordered (D5), lonely
    // nodes absent (XGI parity — only edges' members appear).
    let mut h: Hypergraph = Hypergraph::new();
    h.add_edge(vec!["a".into(), "b".into(), "c".into()], None, Value::Null)
        .unwrap();
    h.add_edge(vec!["b".into(), "c".into()], Some("e1".into()), Value::Null)
        .unwrap();
    h.add_node("lonely", Value::Null);
    let repr = format!("{h:?}");
    assert!(repr.starts_with(v["repr_prefix"].as_str().unwrap()));
    assert_eq!(repr, "Hypergraph([{a, b, c}, {b, c}])");
    // Every fixture-recorded (sorted) member set matches the Rust set.
    for (i, eid) in ["0", "e1"].iter().enumerate() {
        let mut got = h.members(eid).unwrap();
        got.sort();
        assert_eq!(got, ids(&v["members_sorted"][i]));
    }

    let empty: Hypergraph = Hypergraph::new();
    assert_eq!(format!("{empty:?}"), v["repr_empty"].as_str().unwrap());

    // Empty edge: XGI's Python-set artifact "set()" is pinned as truth;
    // Rust formats braces uniformly — "{}" (same D5 class).
    let mut lone_empty: Hypergraph = Hypergraph::new();
    lone_empty.add_edge(vec![], None, Value::Null).unwrap();
    assert_eq!(format!("{lone_empty:?}"), "Hypergraph([{}])");
}

// ---------------------------------------------------------------------------
// DiHypergraph (Phase 2 Task 3+)
// ---------------------------------------------------------------------------

/// Assert a directed edge's (tail, head) against the fixture's sorted lists.
/// Rust returns insertion-ordered vecs (D5); the fixture records sorted, so
/// both sides are sorted before comparison.
fn assert_dimembers(h: &DiHypergraph, edge_id: &str, recorded: &Value) {
    let (mut tail, mut head) = h.dimembers(edge_id).unwrap();
    tail.sort();
    head.sort();
    assert_eq!(tail, ids(&recorded["tail"]));
    assert_eq!(head, ids(&recorded["head"]));
}

#[test]
fn conform_di_add_edge_dimembers() {
    // XGI: add_edge((tail, head)) — tail FIRST, head SECOND; returns None
    // (D8 class: the Rust core returns Ok(id)). dimembers(e) = (tail,
    // head); members(e) = tail ∪ head. dimemberships(n) = (in, out) —
    // "in" = edges where n is in the HEAD, "out" = edges where n is in the
    // TAIL — IN FIRST (probed: tail-only node 1 -> (set(), {0}); head-only
    // node 4 -> ({0}, set())).
    let gt = ground_truth();
    let v = vector(&gt, "di_add_edge_dimembers");
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["dimemberships"]["1"], serde_json::json!([[], ["0"]])); // pinned
    assert_eq!(v["dimemberships"]["4"], serde_json::json!([["0"], []])); // pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    let eid = h
        .add_edge(
            (
                vec!["1".into(), "2".into(), "3".into()],
                vec!["2".into(), "3".into(), "4".into()],
            ),
            None,
            Value::Null,
        )
        .unwrap();
    assert_eq!(eid, id_str(&v["edge_ids"][0]));
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    assert_dimembers(&h, &eid, &v["dimembers"]["0"]);
    assert_eq!(h.tail(&eid).unwrap(), vec!["1", "2", "3"]);
    assert_eq!(h.head(&eid).unwrap(), vec!["2", "3", "4"]);
    assert_eq!(h.members(&eid).unwrap(), vec!["1", "2", "3", "4"]);

    // dimemberships: (head-edges, tail-edges), IN first — XGI's order.
    assert_eq!(
        h.dimemberships("1").unwrap(),
        (Vec::<String>::new(), vec!["0".to_string()])
    );
    assert_eq!(
        h.dimemberships("4").unwrap(),
        (vec!["0".to_string()], Vec::<String>::new())
    );
    for (nid, expected) in v["dimemberships"].as_object().unwrap() {
        let (mut head_edges, mut tail_edges) = h.dimemberships(nid).unwrap();
        head_edges.sort();
        tail_edges.sort();
        assert_eq!(vec![head_edges, tail_edges], ids_nested(expected));
    }
    for (nid, expected) in v["memberships"].as_object().unwrap() {
        let mut got = h.memberships(nid).unwrap();
        got.sort();
        assert_eq!(got, ids(expected));
    }
}

fn ids_nested(v: &Value) -> Vec<Vec<String>> {
    v.as_array().unwrap().iter().map(ids).collect()
}

#[test]
fn conform_di_uid_counter() {
    // DiHypergraph shares update_uid_counter with Hypergraph (probed):
    // auto ids 0, 1; int idx 5 bumps to 6; str "5" no bump; float 5.0
    // bumps; "x" no bump. The Rust core bumps iff idx.parse::<u64>()
    // succeeds — conforming on int-idx, diverging as registered on
    // str-idx (D3) and float-idx (D4).
    let gt = ground_truth();
    let v = vector(&gt, "di_uid_counter");
    assert_eq!(ids(&v["int_idx_bumps"]), vec!["0", "1", "5", "6"]); // XGI truth
    assert_eq!(ids(&v["str_idx_no_bump"]), vec!["5", "0"]); // XGI truth
    assert_eq!(ids(&v["float_idx_bumps"]), vec!["5.0", "6"]); // XGI truth
    assert_eq!(ids(&v["nonnumeric_idx_no_bump"]), vec!["x", "0"]); // XGI truth

    let mut h: DiHypergraph = DiHypergraph::new();
    assert_eq!(
        h.add_edge((vec!["1".into()], vec!["2".into()]), None, Value::Null)
            .unwrap(),
        "0"
    );
    assert_eq!(
        h.add_edge((vec!["3".into()], vec!["4".into()]), None, Value::Null)
            .unwrap(),
        "1"
    );
    h.add_edge(
        (vec!["5".into()], vec!["6".into()]),
        Some("5".into()),
        Value::Null,
    )
    .unwrap();
    // D3: Rust bumps for str-numeric "5" — next auto is "6", not "0".
    let auto = h
        .add_edge((vec!["7".into()], vec!["8".into()]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "6");

    // D4: "5.0" fails parse::<u64>() — no bump.
    let mut h2: DiHypergraph = DiHypergraph::new();
    h2.add_edge(
        (vec!["1".into()], vec!["2".into()]),
        Some("5.0".into()),
        Value::Null,
    )
    .unwrap();
    let auto2 = h2
        .add_edge((vec!["3".into()], vec!["4".into()]), None, Value::Null)
        .unwrap();
    assert_eq!(auto2, "0");
}

#[test]
fn diverge_d2_di_dup_idx_errors_instead_of_warn_noop() {
    // Same D2 error-channel class as the undirected dup-idx: XGI warns +
    // no-ops (returns None); the Rust core returns Err(AlreadyExists) and
    // the binding translates back to UserWarning + None.
    let gt = ground_truth();
    let v = vector(&gt, "di_dup_idx");
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["warned"], true); // XGI truth, pinned
    assert!(v["warning_prefix"]
        .as_str()
        .unwrap()
        .starts_with("uid e1 already exists"));

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["1".into()], vec!["2".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    let err = h.add_edge(
        (vec!["3".into()], vec!["4".into()]),
        Some("e1".into()),
        Value::Null,
    );
    assert!(matches!(err, Err(EdgeError::AlreadyExists { .. })));
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    assert_eq!(h.tail("e1").unwrap(), vec!["1"]);
    assert_eq!(h.head("e1").unwrap(), vec!["2"]);
}

#[test]
fn conform_di_empty_edge() {
    // D1-class parity: add_edge(([], [])) creates an empty directed edge;
    // empty-tail-only and empty-head-only are likewise allowed (probed).
    let gt = ground_truth();
    let v = vector(&gt, "di_empty_edge");
    assert_eq!(v["both_empty"]["return"], Value::Null); // XGI truth, pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    let eid = h.add_edge((vec![], vec![]), None, Value::Null).unwrap();
    assert_eq!(eid, id_str(&v["both_empty"]["edge_ids"][0]));
    assert_eq!(h.num_edges(), 1);
    assert_eq!(h.num_nodes(), 0);
    assert_eq!(
        h.dimembers(&eid).unwrap(),
        (Vec::<String>::new(), Vec::<String>::new())
    );
    assert!(h.members(&eid).unwrap().is_empty());

    let mut h2: DiHypergraph = DiHypergraph::new();
    let e2 = h2
        .add_edge((vec![], vec!["1".into()]), None, Value::Null)
        .unwrap();
    assert_eq!(h2.tail(&e2).unwrap(), Vec::<String>::new());
    assert_eq!(h2.head(&e2).unwrap(), vec!["1"]);

    let mut h3: DiHypergraph = DiHypergraph::new();
    let e3 = h3
        .add_edge((vec!["1".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(h3.tail(&e3).unwrap(), vec!["1"]);
    assert_eq!(h3.head(&e3).unwrap(), Vec::<String>::new());
}

#[test]
fn conform_di_both_directions() {
    // A node listed in BOTH tail and head of the same edge is stored in
    // both sets and survives round-trip; duplicates within one direction
    // are deduped (set semantics per direction, probed).
    let gt = ground_truth();
    let v = vector(&gt, "di_both_directions");
    assert_eq!(v["dimemberships"]["2"], serde_json::json!([["e1"], ["e1"]])); // pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (
            vec!["1".into(), "1".into(), "2".into()],
            vec!["2".into(), "2".into(), "3".into()],
        ),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    assert_eq!(h.tail("e1").unwrap(), vec!["1", "2"]);
    assert_eq!(h.head("e1").unwrap(), vec!["2", "3"]);
    assert_eq!(h.members("e1").unwrap(), vec!["1", "2", "3"]);
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    assert_eq!(
        h.dimemberships("2").unwrap(),
        (vec!["e1".to_string()], vec!["e1".to_string()])
    );
}

#[test]
fn diverge_d14_members_must_be_pair() {
    // D14: XGI raises XGIError "Directed edge must be a list or tuple!"
    // on non-list/tuple members (and a raw TypeError on a list of ints),
    // and XGIError "Invalid direction!" on a bad direction string. The
    // Rust core makes BOTH compile-time-impossible: add_edge takes
    // (Vec<String>, Vec<String>) and direction is the Direction enum —
    // type-level prevention. The Phase 7 binding exposes shims raising
    // XGIError for conformance. XGI's runtime errors are pinned here.
    let gt = ground_truth();
    let v = vector(&gt, "di_members_must_be_pair");
    assert_eq!(v["set_members"]["exception"], "XGIError"); // XGI truth, pinned
    assert_eq!(
        v["set_members"]["message"],
        "Directed edge must be a list or tuple!"
    );
    assert_eq!(v["str_members"]["exception"], "XGIError"); // pinned
    assert_eq!(
        v["str_members"]["message"],
        "Directed edge must be a list or tuple!"
    );
    assert_eq!(v["int_list_members"]["exception"], "TypeError"); // pinned
    assert_eq!(v["invalid_direction"]["exception"], "XGIError"); // pinned
    assert_eq!(v["invalid_direction"]["message"], "Invalid direction!");

    // Rust: the pair shape and the direction vocabulary are types, not
    // runtime checks — this test's existence (it compiles) is the proof.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["1".into()], vec!["2".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    assert_eq!(h.tail("e1").unwrap(), vec!["1"]);
    assert_eq!(h.head("e1").unwrap(), vec!["2"]);
}

#[test]
fn conform_di_add_node_to_edge() {
    // XGI: direction "in" puts the node in the TAIL, "out" in the HEAD;
    // auto-creates a missing edge AND node; returns None; set semantics —
    // re-adding the same (node, direction) is a no-op; adding the same
    // node in the OTHER direction puts it in BOTH sets.
    let gt = ground_truth();
    let v = vector(&gt, "di_add_node_to_edge");
    assert_eq!(v["return_in"], Value::Null); // XGI truth, pinned
    assert_eq!(v["return_out"], Value::Null); // XGI truth, pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node_to_edge("newedge", "newnode", Direction::In); // both missing
    h.add_node_to_edge("e2", "n2", Direction::Out); // both missing
    h.add_edge(
        (vec!["1".into()], vec!["2".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_node_to_edge("e1", "1", Direction::In); // re-add same direction: no-op
    h.add_node_to_edge("e1", "1", Direction::Out); // other direction: BOTH

    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    for (eid, recorded) in v["dimembers"].as_object().unwrap() {
        assert_dimembers(&h, eid, recorded);
    }
    // Node 1 is in BOTH directions of e1.
    assert_eq!(
        h.dimemberships("1").unwrap(),
        (vec!["e1".to_string()], vec!["e1".to_string()])
    );
    for (nid, expected) in v["dimemberships"].as_object().unwrap() {
        let (mut head_edges, mut tail_edges) = h.dimemberships(nid).unwrap();
        head_edges.sort();
        tail_edges.sort();
        assert_eq!(vec![head_edges, tail_edges], ids_nested(expected));
    }
}

#[test]
fn diverge_d11_di_add_node_to_edge_numeric_bumps_counter() {
    // D11-extension (DiHypergraph): XGI's DiHypergraph.add_node_to_edge
    // does NOT call update_uid_counter either — auto-creating numeric
    // edge 5 leaves the next auto id at 0 (the same silent-overwrite
    // footgun as undirected D11: XGI's auto-id add_edge does not
    // existence-check). The Rust core bumps iff the id parses as u64,
    // extending the D3/D11 rule to DiHypergraph.
    let gt = ground_truth();
    let v = vector(&gt, "di_add_node_to_edge");
    assert_eq!(ids(&v["numeric_id_no_bump"]["edge_ids"]), vec!["5", "0"]); // XGI truth

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_node_to_edge("5", "x", Direction::In);
    let auto = h
        .add_edge((vec!["1".into()], vec!["2".into()]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "6"); // Rust divergence, deliberate
    assert_eq!(h.tail("5").unwrap(), vec!["x"]);
    assert_eq!(h.tail("6").unwrap(), vec!["1"]);
    assert_eq!(h.head("6").unwrap(), vec!["2"]);
}

#[test]
fn conform_di_remove_node_from_edge() {
    // XGI: removes ONLY the direction's side; directed "emptied" = BOTH
    // tail AND head empty (an edge with one side still populated survives
    // even with remove_empty=True); remove_empty=False keeps a both-empty
    // edge. Errors are per-direction (a head-only member fails "in").
    let gt = ground_truth();
    let v = vector(&gt, "di_remove_node_from_edge");
    // XGI truth, pinned.
    assert_eq!(
        v["errors"]["missing_edge"]["message"],
        "Edge noedge not in the hypergraph"
    );
    assert_eq!(
        v["errors"]["missing_node"]["message"],
        "Node ghost not in the hypergraph"
    );
    assert_eq!(
        v["errors"]["not_in_tail"]["message"],
        "in-edge e1 does not contain node b"
    );
    assert_eq!(
        v["errors"]["not_in_head"]["message"],
        "out-edge e1 does not contain node b"
    );
    assert_eq!(
        v["errors"]["wrong_direction_member"]["message"],
        "in-edge e1 does not contain node 2"
    );

    // Removes ONLY the direction's side: node 2 leaves the tail but stays
    // in the head.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["1".into(), "2".into()], vec!["2".into(), "3".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.remove_node_from_edge("e1", "2", Direction::In, false)
        .unwrap();
    assert_dimembers(&h, "e1", &v["direction_only"]["dimembers"]["e1"]);
    assert_eq!(
        h.dimemberships("2").unwrap(),
        (vec!["e1".to_string()], Vec::<String>::new())
    );

    // Emptied = BOTH sides: removing the last tail member with the head
    // populated leaves the edge ALIVE even with remove_empty=True.
    let mut h2: DiHypergraph = DiHypergraph::new();
    h2.add_edge(
        (vec!["1".into()], vec!["2".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h2.remove_node_from_edge("e2", "1", Direction::In, true)
        .unwrap();
    assert_eq!(h2.edge_ids(), ids(&v["empty_means_both_sides"]["edge_ids"]));
    assert_dimembers(&h2, "e2", &v["empty_means_both_sides"]["dimembers"]["e2"]);
    // Removing the last head member empties BOTH sides -> dropped.
    h2.remove_node_from_edge("e2", "2", Direction::Out, true)
        .unwrap();
    assert!(h2.edge_ids().is_empty());
    assert_eq!(h2.num_nodes(), 2); // nodes survive

    // remove_empty=False keeps a both-empty edge.
    let mut h3: DiHypergraph = DiHypergraph::new();
    h3.add_edge((vec!["1".into()], vec![]), Some("e3".into()), Value::Null)
        .unwrap();
    h3.remove_node_from_edge("e3", "1", Direction::In, false)
        .unwrap();
    assert_eq!(h3.edge_ids(), ids(&v["keep_empty"]["edge_ids"]));
    assert_eq!(
        h3.dimembers("e3").unwrap(),
        (Vec::<String>::new(), Vec::<String>::new())
    );

    // Errors map to MembershipError variants (D2 channel class).
    let mut he: DiHypergraph = DiHypergraph::new();
    assert_eq!(
        he.remove_node_from_edge("noedge", "a", Direction::In, true),
        Err(MembershipError::EdgeNotFound {
            edge_id: "noedge".to_string()
        })
    );
    let mut hn: DiHypergraph = DiHypergraph::new();
    hn.add_edge(
        (vec!["1".into()], vec!["2".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    assert_eq!(
        hn.remove_node_from_edge("e1", "ghost", Direction::In, true),
        Err(MembershipError::NodeNotFound {
            node_id: "ghost".to_string()
        })
    );
    hn.add_node("b", Value::Null);
    assert_eq!(
        hn.remove_node_from_edge("e1", "b", Direction::In, true),
        Err(MembershipError::NotAMember {
            node_id: "b".to_string(),
            edge_id: "e1".to_string()
        })
    );
    assert_eq!(
        hn.remove_node_from_edge("e1", "b", Direction::Out, true),
        Err(MembershipError::NotAMember {
            node_id: "b".to_string(),
            edge_id: "e1".to_string()
        })
    );
    // Head-only member fails direction In (per-direction membership check).
    assert_eq!(
        hn.remove_node_from_edge("e1", "2", Direction::In, true),
        Err(MembershipError::NotAMember {
            node_id: "2".to_string(),
            edge_id: "e1".to_string()
        })
    );
}

#[test]
fn conform_di_remove_node_modes() {
    // XGI's DiHypergraph.remove_node(n, strong, remove_empty) is
    // three-mode like the undirected (register D9 class): weak drops the
    // node from BOTH directions of every containing edge and removes an
    // edge iff BOTH tail and head are empty AND remove_empty; strong
    // removes every incident edge ENTIRELY, ignoring the flag.
    let gt = ground_truth();
    let v = vector(&gt, "di_remove_node_modes");
    assert_eq!(v["weak_keep"]["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["weak_keep"]["has_node_2"], false); // XGI truth, pinned
    assert_eq!(v["missing_node"]["exception"], "IDNotFound"); // pinned
    assert_eq!(
        v["nodes_from_missing"]["warning_message"],
        "Node ghost not in dihypergraph"
    ); // pinned
    assert_eq!(v["edges_from_missing"]["exception"], "IDNotFound"); // pinned

    // Weak + remove_empty=False: node removed from both directions; an
    // edge emptied on BOTH sides would survive; one-sided edges keep
    // their other side.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["1".into(), "2".into()], vec!["2".into(), "3".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["2".into()], vec!["4".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["5".into()], vec!["2".into()]),
        Some("e3".into()),
        Value::Null,
    )
    .unwrap();
    h.remove_node("2", false, false).unwrap();
    assert_eq!(h.edge_ids(), ids(&v["weak_keep"]["edge_ids"]));
    assert!(!h.has_node("2"));
    for (eid, recorded) in v["weak_keep"]["dimembers"].as_object().unwrap() {
        assert_dimembers(&h, eid, recorded);
    }

    // Weak + remove_empty=True (XGI default): only BOTH-empty edges drop
    // — e2 keeps its head, e5 (tail-only singleton) drops.
    let mut h2: DiHypergraph = DiHypergraph::new();
    h2.add_edge(
        (vec!["2".into()], vec!["4".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h2.add_edge((vec!["2".into()], vec![]), Some("e5".into()), Value::Null)
        .unwrap();
    h2.remove_node("2", false, true).unwrap();
    assert_eq!(h2.edge_ids(), ids(&v["weak_drop"]["edge_ids"]));
    assert_dimembers(&h2, "e2", &v["weak_drop"]["dimembers"]["e2"]);

    // Strong + remove_empty=False: incident edges removed ENTIRELY anyway.
    let mut h3: DiHypergraph = DiHypergraph::new();
    h3.add_edge(
        (vec!["1".into(), "2".into()], vec!["3".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h3.add_edge(
        (vec!["4".into()], vec!["2".into(), "5".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h3.add_edge(
        (vec!["6".into()], vec!["7".into()]),
        Some("e4".into()),
        Value::Null,
    )
    .unwrap();
    h3.remove_node("2", true, false).unwrap();
    assert_eq!(h3.edge_ids(), ids(&v["strong_ignores_flag"]["edge_ids"]));
    assert_dimembers(&h3, "e4", &v["strong_ignores_flag"]["dimembers"]["e4"]);
    let mut rust_nodes = h3.node_ids();
    rust_nodes.sort();
    assert_eq!(rust_nodes, ids(&v["strong_ignores_flag"]["node_ids"]));

    // Missing node: NodeError::NotFound (D2 channel class).
    let mut h4: DiHypergraph = DiHypergraph::new();
    assert!(matches!(
        h4.remove_node("ghost", false, true),
        Err(NodeError::NotFound { .. })
    ));
}

#[test]
fn diverge_d2_di_remove_nodes_from_missing_warns_per_item() {
    // XGI's DiHypergraph.remove_nodes_from WARNS "Node ghost not in
    // dihypergraph" (note: "dihypergraph" — the undirected message says
    // "hypergraph"), SKIPS, CONTINUES; returns None. D2-class channel
    // translation: per-item Err(NodeError::NotFound) in the Vec; the
    // binding warns per Err item.
    let gt = ground_truth();
    let v = vector(&gt, "di_remove_node_modes")["nodes_from_missing"].clone();
    assert_eq!(v["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["warned"], true); // XGI truth, pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["1".into(), "2".into()], vec!["3".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    let results = h.remove_nodes_from(
        vec!["1".to_string(), "ghost".to_string(), "2".to_string()],
        false,
        true,
    );
    assert_eq!(results.len(), 3);
    assert!(results[0].is_ok());
    assert_eq!(
        results[1],
        Err(NodeError::NotFound {
            node_id: "ghost".to_string()
        })
    );
    assert!(results[2].is_ok(), "continues past the missing id");
    assert_eq!(h.node_ids(), ids(&v["node_ids"]));
    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    // e1's tail emptied (1 and 2 removed) but head {3} survives — e1 lives.
    assert_dimembers(&h, "e1", &v["dimembers"]["e1"]);
}

#[test]
fn diverge_d2_di_remove_edges_from_missing_stops_after_err() {
    // XGI's DiHypergraph.remove_edges_from RAISES IDNotFound mid-iteration
    // — ids before the miss are already removed, ids after never attempted
    // (["e1", "ghost", "e3"] leaves e2 AND e3). D2-class channel
    // translation: per-item results, STOP after the first Err.
    let gt = ground_truth();
    let v = vector(&gt, "di_remove_node_modes")["edges_from_missing"].clone();
    assert_eq!(v["message"], "'ID ghost not found'"); // XGI truth, pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["1".into()], vec!["2".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["2".into()], vec!["3".into()]),
        Some("e2".into()),
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["3".into()], vec!["4".into()]),
        Some("e3".into()),
        Value::Null,
    )
    .unwrap();
    let results = h.remove_edges_from(vec![
        "e1".to_string(),
        "ghost".to_string(),
        "e3".to_string(),
    ]);
    assert_eq!(results.len(), 2, "e3 was never attempted");
    assert!(results[0].is_ok());
    assert_eq!(
        results[1],
        Err(EdgeError::NotFound {
            edge_id: "ghost".to_string()
        })
    );
    assert_eq!(h.edge_ids(), ids(&v["edge_ids_after"])); // e2 AND e3 survive
}

#[test]
fn diverge_d2_di_remove_edge_missing_errors() {
    // Same D2 error-channel class: XGI raises IDNotFound on a missing edge;
    // the Rust core returns Err(EdgeError::NotFound) and the binding
    // translates Err → raise.
    let gt = ground_truth();
    let v = vector(&gt, "di_remove_node_modes")["remove_edge_missing"].clone();
    assert_eq!(v["exception"], "IDNotFound"); // XGI truth, pinned
    assert_eq!(v["message"], "'ID ghost not found'"); // XGI truth, pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    assert!(matches!(
        h.remove_edge("ghost"),
        Err(EdgeError::NotFound { .. })
    ));
}

// ---------------------------------------------------------------------------
// DiHypergraph bulk/attrs/copy/clear/freeze/Debug/eq (Phase 2 Task 5)
// ---------------------------------------------------------------------------

#[test]
fn conform_di_repr_format() {
    // XGI's DiHypergraph.__repr__ is f"{cls}({self.edges.dimembers()})" —
    // the class name wrapping a list of (tail, head) set-tuples, edges in
    // insertion order. The Rust core's Debug produces the same SHAPE
    // (DiHypergraph([({tail}, {head}), ...])) with members in INSERTION
    // order and uniform braces — cited divergence D5 (XGI's member sets
    // are hash-ordered; the fixture records sorted projections only).
    // XGI renders an empty side as "set()"; Rust formats "{}" — same D5
    // class. Lonely nodes never appear (XGI parity).
    let gt = ground_truth();
    let v = vector(&gt, "di_repr");
    assert_eq!(v["repr_prefix"], "DiHypergraph("); // XGI truth, pinned
    assert_eq!(v["repr_empty"], "DiHypergraph([])"); // XGI truth, pinned
    assert_eq!(v["repr_both_empty_edge"], "DiHypergraph([(set(), set())])"); // pinned
    assert_eq!(
        v["dimembers_sorted"],
        serde_json::json!([[["a", "b", "c"], ["b", "d"]], [["a"], []]])
    ); // XGI truth (sorted), pinned

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
    h.add_node("lonely", Value::Null);
    let repr = format!("{h:?}");
    assert!(repr.starts_with(v["repr_prefix"].as_str().unwrap()));
    assert_eq!(repr, "DiHypergraph([({a, b, c}, {b, d}), ({a}, {})])");
    // Every fixture-recorded (sorted) side matches the Rust side.
    for (i, eid) in ["0", "e1"].iter().enumerate() {
        let (mut tail, mut head) = h.dimembers(eid).unwrap();
        tail.sort();
        head.sort();
        assert_eq!(vec![tail, head], ids_nested(&v["dimembers_sorted"][i]));
    }

    let empty: DiHypergraph = DiHypergraph::new();
    assert_eq!(format!("{empty:?}"), v["repr_empty"].as_str().unwrap());

    // Both-empty edge: XGI's "(set(), set())" artifact is pinned as
    // truth; Rust formats braces uniformly — "({}, {})" (same D5 class).
    let mut both_empty: DiHypergraph = DiHypergraph::new();
    both_empty
        .add_edge((vec![], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(format!("{both_empty:?}"), "DiHypergraph([({}, {})])");
}

#[test]
fn conform_di_eq_structural() {
    // XGI's DiHypergraph.__eq__ delegates to xgi.algorithms.equal with
    // the defaults: the edge-id -> {"in": tail, "out": head} mapping,
    // node attrs, edge attrs, and net attrs are all significant;
    // member order is not. DIRECTION IS SIGNIFICANT (probed: tail/head
    // swapped -> NOT equal; both-directions vs tail-only -> NOT equal).
    // The Rust core's PartialEq matches every recorded verdict.
    let gt = ground_truth();
    let v = vector(&gt, "di_eq");
    // XGI truth, pinned.
    assert_eq!(v["same"], true);
    assert_eq!(v["direction_flipped"], false);
    assert_eq!(v["member_order_insignificant"], true);
    assert_eq!(v["diff_edge_id"], false);
    assert_eq!(v["diff_edge_attr"], false);
    assert_eq!(v["lonely_same"], true);
    assert_eq!(v["diff_node_attr"], false);
    assert_eq!(v["lonely_missing"], false);
    assert_eq!(v["diff_net_attr"], false);
    assert_eq!(v["both_vs_tail_only"], false);
    assert_eq!(v["empty_attr_lonely_vs_absent"], false);

    let build = |tail: &[&str],
                 head: &[&str],
                 idx: &str,
                 edge_attr: Value,
                 solo: Option<(&str, Value)>,
                 net: Option<(&str, Value)>| {
        let mut h: DiHypergraph = DiHypergraph::new();
        h.add_edge(
            (
                tail.iter().map(|m| m.to_string()).collect(),
                head.iter().map(|m| m.to_string()).collect(),
            ),
            Some(idx.into()),
            edge_attr,
        )
        .unwrap();
        if let Some((n, attrs)) = solo {
            h.add_node(n, attrs);
        }
        if let Some((k, val)) = net {
            h.set_graph_attr(k, val);
        }
        h
    };
    let a = build(&["a", "b"], &["c"], "e1", Value::Null, None, None);
    assert_eq!(a, build(&["a", "b"], &["c"], "e1", Value::Null, None, None));
    // Direction flipped -> NOT equal.
    assert_ne!(a, build(&["c"], &["a", "b"], "e1", Value::Null, None, None));
    // Member order insignificant.
    assert_eq!(a, build(&["b", "a"], &["c"], "e1", Value::Null, None, None));
    // Edge id significant.
    assert_ne!(a, build(&["a", "b"], &["c"], "e2", Value::Null, None, None));
    // Edge attrs significant.
    assert_ne!(
        build(
            &["a", "b"],
            &["c"],
            "e1",
            serde_json::json!({"w": 1}),
            None,
            None
        ),
        build(
            &["a", "b"],
            &["c"],
            "e1",
            serde_json::json!({"w": 2}),
            None,
            None
        )
    );
    // Net attrs significant.
    assert_ne!(
        a,
        build(
            &["a", "b"],
            &["c"],
            "e1",
            Value::Null,
            None,
            Some(("name", serde_json::json!("x")))
        )
    );
    // Both-directions vs tail-only -> NOT equal.
    assert_ne!(
        build(&["a", "b"], &["b"], "e1", Value::Null, None, None),
        build(&["a", "b"], &[], "e1", Value::Null, None, None)
    );
    // Lonely node attrs significant; presence significant (even with
    // EMPTY attrs — XGI compares _node_attr, where every node carries a
    // dict).
    let l1 = build(
        &["a", "b"],
        &["c"],
        "e1",
        Value::Null,
        Some(("solo", serde_json::json!({"color": "red"}))),
        None,
    );
    let l2 = build(
        &["a", "b"],
        &["c"],
        "e1",
        Value::Null,
        Some(("solo", serde_json::json!({"color": "red"}))),
        None,
    );
    let l3 = build(
        &["a", "b"],
        &["c"],
        "e1",
        Value::Null,
        Some(("solo", serde_json::json!({"color": "blue"}))),
        None,
    );
    assert_eq!(l1, l2);
    assert_ne!(l1, l3);
    assert_ne!(l1, a);
    let e1 = build(
        &["a", "b"],
        &["c"],
        "e1",
        Value::Null,
        Some(("solo", serde_json::json!({}))),
        None,
    );
    assert_ne!(e1, a);
}

#[test]
fn conform_di_add_edges_from() {
    // XGI's add_edges_from accepts members-only (auto ids), (members,
    // idx), (members, attrdict), (members, idx, attrdict), and dict
    // bunches, plus **attr broadcast (per-edge attrs take precedence);
    // returns None. The Rust core takes uniform (tail, head, idx,
    // attrs) quadruples — format detection and broadcast merging are
    // binding concerns (D7 class); the outcomes conform. The Notes
    // claim empty edges are skipped — the runtime CREATES one for
    // ([], []) (D1-class docstring lie); the core conforms.
    let gt = ground_truth();
    let v = vector(&gt, "di_add_edges_from");
    assert_eq!(v["members_only"]["return"], Value::Null); // XGI truth, pinned
    assert_eq!(v["dup_warns_continues"]["return"], Value::Null); // pinned
    assert_eq!(v["dup_warns_continues"]["warned"], true); // pinned
    assert!(v["dup_warns_continues"]["warning_prefix"]
        .as_str()
        .unwrap()
        .starts_with("uid e1 already exists"));
    // Broadcast: per-edge color wins, size merges in — XGI truth, pinned.
    assert_eq!(
        v["broadcast"],
        serde_json::json!({"0": {"color": "red", "size": 10}})
    );

    // Members-only: auto ids in order.
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
            vec!["e".into(), "f".into()],
            None,
            Value::Null,
        ),
    ]);
    assert!(results.iter().all(|r| r.is_ok()));
    assert_eq!(h.edge_ids(), ids(&v["members_only"]["edge_ids"]));
    for (eid, recorded) in v["members_only"]["dimembers"].as_object().unwrap() {
        assert_dimembers(&h, eid, recorded);
    }

    // (members, idx, attrs): ids and per-edge attrs land.
    let mut h2: DiHypergraph = DiHypergraph::new();
    h2.add_edges_from(vec![
        (
            vec!["a".into()],
            vec!["b".into()],
            Some("one".into()),
            serde_json::json!({"color": "red"}),
        ),
        (
            vec!["c".into()],
            vec![],
            Some("two".into()),
            serde_json::json!({"color": "blue", "age": 40}),
        ),
    ]);
    assert_eq!(h2.edge_ids(), ids(&v["with_idx_attrs"]["edge_ids"]));
    for (eid, attrs) in v["with_idx_attrs"]["attrs"].as_object().unwrap() {
        assert_eq!(h2.edge_attrs(eid).unwrap(), attrs);
    }
    for (eid, recorded) in v["with_idx_attrs"]["dimembers"].as_object().unwrap() {
        assert_dimembers(&h2, eid, recorded);
    }

    // Broadcast equivalence: the binding merges **attr into each edge's
    // dict (per-edge wins) before calling; the core receives the merged
    // attrs — the outcome matches XGI's recorded broadcast result.
    let mut h3: DiHypergraph = DiHypergraph::new();
    h3.add_edges_from(vec![(
        vec!["a".into()],
        vec!["b".into()],
        None,
        serde_json::json!({"color": "red", "size": 10}),
    )]);
    assert_eq!(h3.edge_attrs("0").unwrap(), &v["broadcast"]["0"]);

    // Empty edge is CREATED, not skipped (D1-class).
    let mut h4: DiHypergraph = DiHypergraph::new();
    h4.add_edges_from(vec![
        (vec![], vec![], None, Value::Null),
        (vec!["a".into()], vec!["b".into()], None, Value::Null),
    ]);
    assert_eq!(h4.edge_ids(), ids(&v["empty_created"]["edge_ids"]));
    for (eid, recorded) in v["empty_created"]["dimembers"].as_object().unwrap() {
        assert_dimembers(&h4, eid, recorded);
    }
}

#[test]
fn diverge_d2_di_add_edges_from_dup_errors_continues() {
    // Same D2 error-channel class as the undirected bulk add: XGI warns
    // + skips a duplicate idx and CONTINUES with the rest (the dup's
    // members are never added). The Rust core surfaces the dup as
    // Err(AlreadyExists) in the per-edge Vec<Result> and continues; the
    // binding translates Err -> UserWarning + skip.
    let gt = ground_truth();
    let v = vector(&gt, "di_add_edges_from")["dup_warns_continues"].clone();

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
    assert_eq!(results.len(), 3);
    assert!(results[0].is_ok());
    assert!(matches!(results[1], Err(EdgeError::AlreadyExists { .. })));
    assert!(results[2].is_ok(), "continues past the dup");

    // Dup skipped, the rest kept — XGI's recorded final state.
    assert_eq!(h.edge_ids(), ids(&v["edge_ids"]));
    assert_eq!(h.num_nodes(), v["num_nodes"].as_u64().unwrap() as usize);
    for (eid, recorded) in v["dimembers"].as_object().unwrap() {
        assert_dimembers(&h, eid, recorded);
    }
}

#[test]
fn conform_di_set_attrs() {
    // set_node_attributes / set_edge_attributes mirror the undirected
    // class: dict-of-dicts MERGES into existing attr dicts; a missing id
    // warns + SKIPS, never auto-creates (the warn channel is a binding
    // concern — D2 class); a list of pairs raises XGIError at XGI's
    // Python boundary (the core takes pairs — D7 class); the scalar and
    // dict-of-scalars name= forms are binding sugar (their outcomes are
    // pinned as XGI truth; the core's per-node merge produces them).
    let gt = ground_truth();
    let v = vector(&gt, "di_set_attrs");
    // XGI truth, pinned.
    assert_eq!(v["node_dict_of_dicts"]["return"], Value::Null);
    assert_eq!(v["node_dict_of_dicts"]["warned"], true);
    assert_eq!(
        v["node_dict_of_dicts"]["warning_message"],
        "Node ghost does not exist!"
    );
    assert_eq!(v["node_pairs_exception"], "XGIError");
    assert_eq!(
        v["node_pairs_message"],
        "Must pass a dictionary of dictionaries"
    );
    assert_eq!(
        v["node_dict_of_dicts"]["attrs_a"],
        serde_json::json!({"x": 1, "color": "red"})
    );
    assert_eq!(v["edge_dict_of_dicts"]["return"], Value::Null);
    assert_eq!(v["edge_dict_of_dicts"]["warned"], true);
    assert_eq!(
        v["edge_dict_of_dicts"]["warning_message"],
        "Edge ghost does not exist!"
    );
    assert_eq!(
        v["edge_dict_of_dicts"]["attrs_e1"],
        serde_json::json!({"w": 1, "heat": 0.5})
    );
    // Scalar broadcast + dict-of-scalars name= forms: XGI truth, pinned.
    assert_eq!(
        v["node_scalar_broadcast"]["attrs_a"],
        serde_json::json!({"color": "red"})
    );
    assert_eq!(
        v["node_scalar_broadcast"]["attrs_c"],
        serde_json::json!({"color": "red"})
    );
    assert_eq!(
        v["node_dict_of_scalars"]["attrs_a"],
        serde_json::json!({"color": "red"})
    );
    assert_eq!(v["node_dict_of_scalars"]["attrs_b"], serde_json::json!({}));

    // Node dict-of-dicts: merge; ghost skipped, never auto-created.
    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    *h.node_attrs_mut("a").unwrap() = serde_json::json!({"x": 1});
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
        &v["node_dict_of_dicts"]["attrs_a"]
    );
    assert_eq!(
        h.node_attrs("b").unwrap(),
        &v["node_dict_of_dicts"]["attrs_b"]
    );
    assert!(!h.has_node("ghost"));
    assert_eq!(
        h.num_nodes(),
        v["node_dict_of_dicts"]["num_nodes"].as_u64().unwrap() as usize
    );

    // Edge dict-of-dicts: merge; ghost skipped.
    let mut h2: DiHypergraph = DiHypergraph::new();
    h2.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e1".into()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    h2.add_edge(
        (vec!["c".into()], vec!["d".into()]),
        Some("e2".into()),
        serde_json::json!({}),
    )
    .unwrap();
    let mut heat = serde_json::Map::new();
    heat.insert("heat".to_string(), serde_json::json!(0.5));
    let mut x = serde_json::Map::new();
    x.insert("x".to_string(), serde_json::json!(1));
    h2.set_edge_attributes(vec![("e1".to_string(), heat), ("ghost".to_string(), x)]);
    assert_eq!(
        h2.edge_attrs("e1").unwrap(),
        &v["edge_dict_of_dicts"]["attrs_e1"]
    );
    assert_eq!(
        h2.edge_attrs("e2").unwrap(),
        &v["edge_dict_of_dicts"]["attrs_e2"]
    );
    assert!(!h2.has_edge("ghost"));
    assert_eq!(
        h2.num_edges(),
        v["edge_dict_of_dicts"]["num_edges"].as_u64().unwrap() as usize
    );
}

#[test]
fn diverge_d10_di_clear_resets_uid_counter() {
    // DiHypergraph.clear() empties nodes, edges, all attr channels, and
    // net attrs — the Rust core conforms on all of that. D10 (extended
    // to DiHypergraph): XGI does NOT reset its auto-id counter (the next
    // auto id continues at 1); the Rust core resets edge_uid_counter —
    // clear() ≡ new() (III.7 replay-from-empty determinism).
    let gt = ground_truth();
    let v = vector(&gt, "di_clear_freeze")["clear"].clone();
    assert_eq!(v["num_nodes"], 0); // XGI truth, pinned
    assert_eq!(v["num_edges"], 0);
    assert_eq!(v["node_ids"], serde_json::json!([]));
    assert_eq!(v["edge_ids"], serde_json::json!([]));
    assert_eq!(v["net_attrs"], serde_json::json!({}));
    assert_eq!(ids(&v["auto_ids_after_clear"]), vec!["1"]); // XGI truth, pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        None,
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["d".into()], vec!["e".into()]),
        Some("e1".into()),
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
    assert!(h.node_attrs("lonely").is_none());
    assert!(h.edge_attrs("e1").is_none());

    // D10: Rust resets the counter — the post-clear auto id is "0".
    let auto = h
        .add_edge((vec!["z".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "0"); // Rust divergence, deliberate
}

#[test]
fn diverge_d16_di_clear_edges_is_core_extension() {
    // D16: XGI's DiHypergraph HAS NO clear_edges — the attribute lookup
    // falls through XGI's __getattr__ stat fallback and raises
    // AttributeError (pinned below). The Rust core provides clear_edges
    // for API uniformity with Hypergraph: it removes every edge, keeps
    // all nodes/attrs/net attrs, and (like the undirected core) does NOT
    // reset the uid counter. Freeze-guarded per the D12 uniform-guard
    // rationale.
    let gt = ground_truth();
    let v = vector(&gt, "di_clear_freeze")["freeze"]["guarded"]["clear_edges"].clone();
    assert_eq!(v["exception"], "AttributeError"); // XGI truth, pinned
    assert!(v["message"]
        .as_str()
        .unwrap()
        .starts_with("clear_edges is not a method of DiHypergraph"));

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        None,
        Value::Null,
    )
    .unwrap();
    h.add_edge(
        (vec!["d".into()], vec!["e".into()]),
        Some("e1".into()),
        serde_json::json!({"heat": 0.5}),
    )
    .unwrap();
    h.add_node("lonely", serde_json::json!({"x": 1}));
    h.set_graph_attr("name", serde_json::json!("test"));
    h.clear_edges();

    assert_eq!(h.num_edges(), 0);
    assert_eq!(h.num_nodes(), 6, "nodes survive");
    assert_eq!(
        h.node_attrs("lonely").unwrap(),
        &serde_json::json!({"x": 1})
    );
    assert_eq!(
        h.graph_attr("name"),
        Some(&serde_json::json!("test")),
        "net attrs survive"
    );
    assert!(h.memberships("a").unwrap().is_empty());

    // Counter NOT reset (uniformity with Hypergraph.clear_edges — the
    // node state survives, so counter continuity matches state
    // continuity): the next auto id is "1".
    let auto = h
        .add_edge((vec!["z".into()], vec![]), None, Value::Null)
        .unwrap();
    assert_eq!(auto, "1");
}

#[test]
fn conform_di_freeze_blocks_mutation() {
    // XGI's DiHypergraph.freeze() guards add_node(s)_from,
    // add_edge(s)_from, remove_node(s)_from, remove_edge(s)_from, and
    // clear (XGIError "Frozen higher-order network can't be modified").
    // The Rust core panics on the same mutators (panic ≡ raise; the
    // binding converts — D2 error-channel class). The attr-dict channel
    // (set_node_attributes / set_edge_attributes) is unguarded in XGI —
    // the Rust core matches.
    let gt = ground_truth();
    let v = vector(&gt, "di_clear_freeze")["freeze"].clone();
    assert_eq!(v["is_frozen_before"], false); // XGI truth, pinned
    assert_eq!(v["is_frozen_after"], true); // XGI truth, pinned
    for method in [
        "add_node",
        "add_nodes_from",
        "add_edge",
        "add_edges_from",
        "remove_node",
        "remove_nodes_from",
        "remove_edge",
        "remove_edges_from",
        "clear",
    ] {
        assert_eq!(v["guarded"][method]["exception"], "XGIError"); // pinned
        assert_eq!(
            v["guarded"][method]["message"],
            "Frozen higher-order network can't be modified"
        );
    }
    // The attr-dict channel is NOT guarded in XGI — pinned as truth.
    assert_eq!(v["guarded"]["set_node_attributes"], Value::Null);
    assert_eq!(v["guarded"]["set_edge_attributes"], Value::Null);

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        Some("e1".into()),
        serde_json::json!({"w": 1}),
    )
    .unwrap();
    assert!(!h.is_frozen());
    h.freeze();
    assert!(h.is_frozen());

    let mut panics = |f: &mut dyn FnMut(&mut DiHypergraph)| {
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| f(&mut h))).is_err()
    };
    assert!(panics(&mut |h| {
        h.add_node("z", Value::Null);
    }));
    assert!(panics(&mut |h| {
        h.add_nodes_from(vec![("z".to_string(), Value::Null)]);
    }));
    assert!(panics(&mut |h| {
        h.add_edge((vec!["a".into()], vec!["b".into()]), None, Value::Null)
            .unwrap();
    }));
    assert!(panics(&mut |h| {
        h.add_edges_from(vec![(
            vec!["a".into()],
            vec!["b".into()],
            None,
            Value::Null,
        )]);
    }));
    assert!(panics(&mut |h| h.remove_node("a", false, true).unwrap()));
    assert!(panics(&mut |h| {
        h.remove_nodes_from(vec!["a".to_string()], false, true);
    }));
    assert!(panics(&mut |h| h.remove_edge("e1").unwrap()));
    assert!(panics(&mut |h| {
        h.remove_edges_from(vec!["e1".to_string()]);
    }));
    assert!(panics(&mut |h| h.clear()));

    // XGI parity: the attr-dict channel stays OPEN on a frozen graph.
    let mut attrs = serde_json::Map::new();
    attrs.insert("k".to_string(), serde_json::json!(1));
    h.set_node_attributes(vec![("a".to_string(), attrs.clone())]);
    h.set_edge_attributes(vec![("e1".to_string(), attrs)]);
    assert_eq!(h.node_attrs("a").unwrap()["k"], 1);
    assert_eq!(h.edge_attrs("e1").unwrap()["k"], 1);
}

#[test]
fn diverge_d12_di_freeze_guards_membership_ops_and_clear_edges() {
    // D12 (extended to DiHypergraph): XGI's DiHypergraph freeze list
    // omits add_node_to_edge AND remove_node_from_edge (unlike the
    // undirected class, which guards both) — probed: both mutate a
    // FROZEN DiHypergraph unimpeded. clear_edges does not exist at all
    // (D16). The Rust core's frozen flag guards ALL structural mutators
    // uniformly — a freeze that permits membership surgery or wholesale
    // edge deletion is not a freeze.
    let gt = ground_truth();
    let v = vector(&gt, "di_clear_freeze")["freeze"].clone();
    assert_eq!(v["guarded"]["add_node_to_edge"], Value::Null); // XGI truth, pinned
    assert_eq!(v["guarded"]["remove_node_from_edge"], Value::Null); // pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into(), "b".into()], vec!["c".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.freeze();
    let r1 = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        h.add_node_to_edge("e1", "n", Direction::In);
    }));
    assert!(
        r1.is_err(),
        "Rust divergence: add_node_to_edge panics when frozen"
    );
    let r2 = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        h.remove_node_from_edge("e1", "a", Direction::In, true)
            .unwrap();
    }));
    assert!(
        r2.is_err(),
        "Rust divergence: remove_node_from_edge panics when frozen"
    );
    let r3 = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| h.clear_edges()));
    assert!(
        r3.is_err(),
        "Rust divergence: clear_edges panics when frozen"
    );
    // The panics fired BEFORE any mutation: the original is untouched.
    assert_eq!(h.tail("e1").unwrap(), vec!["a", "b"]);
    assert!(!h.has_node("n"));
    assert_eq!(h.num_edges(), 1);
}

#[test]
fn diverge_d13_di_copy_carries_frozen() {
    // D13 (DiHypergraph parity): XGI's freeze is per-instance
    // method-swizzling — copy() of a frozen DiHypergraph is NOT frozen
    // (pinned). The Rust core's frozen flag is data; copy() carries it.
    let gt = ground_truth();
    let v = vector(&gt, "di_clear_freeze")["freeze"].clone();
    assert_eq!(v["copy_of_frozen_is_frozen"], false); // XGI truth, pinned

    let mut h: DiHypergraph = DiHypergraph::new();
    h.add_edge(
        (vec!["a".into()], vec!["b".into()]),
        Some("e1".into()),
        Value::Null,
    )
    .unwrap();
    h.freeze();
    let cp = h.copy();
    assert!(cp.is_frozen(), "Rust divergence: copy of frozen is frozen");
}
