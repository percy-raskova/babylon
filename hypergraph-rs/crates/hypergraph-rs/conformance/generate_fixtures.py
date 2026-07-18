"""Generate XGI ground-truth conformance fixtures for hypergraph-rs.

Runs the ACTUAL installed XGI (never its docstrings) and records observed
behavior as committed JSON. The Rust replay test
(``tests/conformance/main.rs``) replays every vector and encodes the
deliberate divergences as an executable register (D1, D2, ...).

Regenerate deliberately, never silently:

    mise run rust:fixtures

Determinism: no wall-clock, no randomness, all sets sorted, keys ordered.
The file is reviewed data — a diff means XGI behavior changed (version
bump) or the generator did. Both are news; investigate before committing.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import xgi

OUT = Path(__file__).with_name("xgi_ground_truth.json")


def _ids(H: xgi.Hypergraph) -> list:
    return list(H.edges)


def _members_sorted(H: xgi.Hypergraph) -> dict:
    return {str(e): sorted(str(n) for n in H.edges.members(e)) for e in H.edges}


def v_add_edge_empty_creates_edge() -> dict:
    H = xgi.Hypergraph()
    ret = H.add_edge([])
    return {
        "return": ret,
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "edge_ids": _ids(H),
        "members": _members_sorted(H),
    }


def v_add_edge_three_empty_auto_ids() -> dict:
    H = xgi.Hypergraph()
    for _ in range(3):
        H.add_edge([])
    return {"edge_ids": _ids(H), "num_edges": H.num_edges}


def v_add_edge_dup_idx_warns_noop() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a"], idx="e1")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = H.add_edge(["b"], idx="e1")
    return {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_prefix": str(caught[0].message)[:22] if caught else None,
        "num_edges": H.num_edges,
        "members": _members_sorted(H),
    }


def v_add_edge_int_idx_bumps_counter() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a"], idx=5)
    H.add_edge(["b"])
    return {"edge_ids": _ids(H)}


def v_add_edge_str_idx_no_bump() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a"], idx="5")
    H.add_edge(["b"])
    return {"edge_ids": _ids(H)}


def v_add_edge_float_idx_bumps() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a"], idx=5.0)
    H.add_edge(["b"])
    return {"edge_ids": _ids(H)}


def v_add_node_existing_updates_attrs() -> dict:
    H = xgi.Hypergraph()
    H.add_node("a", x=1)
    H.add_node("a", y=2)
    return {"attrs": dict(H.nodes["a"]), "num_nodes": H.num_nodes}


def v_add_edge_dedups_members() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a", "a", "b"], idx="e1")
    return {"members": _members_sorted(H), "num_nodes": H.num_nodes}


def v_add_edge_auto_ids_sequence() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a"])
    H.add_edge(["b"])
    return {"edge_ids": _ids(H)}


def v_remove_edge_basic() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["a", "c"], idx="e2")
    H.remove_edge("e1")
    return {
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "node_ids": sorted(str(n) for n in H.nodes),
        "members": _members_sorted(H),
        "memberships": {str(n): sorted(str(e) for e in H.nodes.memberships(n)) for n in H.nodes},
    }


def v_remove_edge_missing_raises() -> dict:
    H = xgi.Hypergraph()
    try:
        H.remove_edge("nonexistent")
    except Exception as exc:  # recording the observed type IS the vector
        return {"exception": type(exc).__name__, "message": str(exc)}
    return {"exception": None, "message": None}


def v_remove_node_weak() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a", "b", "c"], idx="e1")
    H.add_edge(["b", "d"], idx="e2")
    H.add_edge(["b"], idx="e3")  # weak removal of b empties e3 -> removed (remove_empty=True)
    H.remove_node("b")  # strong=False, remove_empty=True — the XGI defaults
    return {
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "node_ids": sorted(str(n) for n in H.nodes),
        "members": _members_sorted(H),
        "memberships": {str(n): sorted(str(e) for e in H.nodes.memberships(n)) for n in H.nodes},
    }


def v_remove_node_strong() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["a", "c", "d"], idx="e2")
    H.add_edge(["c", "d"], idx="e4")
    H.remove_node("a", strong=True)
    return {
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "node_ids": sorted(str(n) for n in H.nodes),
        "members": _members_sorted(H),
        "memberships": {str(n): sorted(str(e) for e in H.nodes.memberships(n)) for n in H.nodes},
    }


def v_remove_node_missing_raises() -> dict:
    H = xgi.Hypergraph()
    try:
        H.remove_node("nonexistent")
    except Exception as exc:  # recording the observed type IS the vector
        return {"exception": type(exc).__name__, "message": str(exc)}
    return {"exception": None, "message": None}


def v_remove_edge_then_readd() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.remove_edge("e1")
    H.add_edge(["c"], idx="e1")  # fresh members — a/b must NOT resurrect
    ret = H.add_edge(["d"])  # auto id — does the counter reuse the removed id?
    return {
        "return": ret,
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "node_ids": sorted(str(n) for n in H.nodes),
        "members": _members_sorted(H),
    }


def v_node_attr_set_read() -> dict:
    H = xgi.Hypergraph()
    H.add_node("a")
    H.nodes["a"]["color"] = "red"  # in-place attr-dict mutation (XGI-facing)
    return {"attrs": dict(H.nodes["a"])}


def v_clear_all() -> dict:
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"])  # auto id 0 — bumps XGI's uid counter
    H.add_edge(["c", "d"], idx="e1", heat=0.5)
    H.add_node("lonely", x=1)
    H["name"] = "test"
    H.clear()  # remove_net_attr=True is the XGI default
    state = {
        "num_nodes": H.num_nodes,
        "num_edges": H.num_edges,
        "node_ids": sorted(str(n) for n in H.nodes),
        "edge_ids": _ids(H),
        "net_attrs": dict(H._net_attr),
    }
    # XGI's clear() empties nodes/edges/attrs but does NOT reset the auto-id
    # counter: the next auto id continues at 1. Pinned for divergence D8 —
    # the Rust core resets its counter (clear() ≡ new()).
    H.add_edge(["z"])
    state["auto_ids_after_clear"] = _ids(H)
    return state


def main() -> None:
    vectors = {
        name.removeprefix("v_"): fn()
        for name, fn in sorted(globals().items())
        if name.startswith("v_") and callable(fn)
    }
    payload = {
        "xgi_version": xgi.__version__,
        "generated_by": "conformance/generate_fixtures.py",
        "vectors": vectors,
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT} ({len(vectors)} vectors, xgi {xgi.__version__})")


if __name__ == "__main__":
    main()
