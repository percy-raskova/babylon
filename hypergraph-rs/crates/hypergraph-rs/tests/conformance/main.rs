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

use hypergraph_rs::{EdgeError, Hypergraph, MembershipError, NodeError};
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
