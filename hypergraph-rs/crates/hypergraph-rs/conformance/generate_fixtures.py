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
    # counter: the next auto id continues at 1. Pinned for divergence D10 —
    # the Rust core resets its counter (clear() ≡ new()).
    H.add_edge(["z"])
    state["auto_ids_after_clear"] = _ids(H)
    return state


def v_add_edges_from_dup_warns_continues() -> dict:
    H = xgi.Hypergraph()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = H.add_edges_from([(["a"], "e1"), (["b"], "e1"), (["c"], "e2")])
    # XGI warns + skips the duplicate idx and CONTINUES with the rest; the
    # dup's members ("b") are never added (the no-op precedes member
    # insertion, as in v_add_edge_dup_idx_warns_noop).
    return {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_prefix": str(caught[0].message)[:22] if caught else None,
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "members": _members_sorted(H),
    }


def v_eq_structural() -> dict:
    # XGI's Hypergraph.__eq__ delegates to xgi.algorithms.equal with the
    # defaults (compare_edge_ids=True, compare_attrs=True): equal iff the
    # edge-id -> members mapping, node attrs, edge attrs, and net attrs are
    # all equal. Insertion/member order is INSIGNIFICANT (sets); edge IDs
    # and every attr channel are SIGNIFICANT.
    def build(members, idx, edge_attr=None, node_attrs=None, net=None):
        H = xgi.Hypergraph()
        H.add_edge(list(members), idx=idx, **(edge_attr or {}))
        for n, a in (node_attrs or {}).items():
            if n in H:
                H.nodes[n].update(a)
            else:
                H.add_node(n, **a)
        for k, val in (net or {}).items():
            H[k] = val
        return H

    A = build(["a", "b"], "e1", {"w": 1})
    return {
        "same": build(["a", "b"], "e1", {"w": 1}) == A,
        "diff_edge_attr": build(["a", "b"], "e1", {"w": 2}) == A,
        "diff_members": build(["a", "c"], "e1") == A,
        "diff_edge_id": build(["a", "b"], "e2") == A,
        "diff_net_attr": build(["a", "b"], "e1", {"w": 1}, net={"name": "x"}) == A,
        "member_order_insignificant": build(["b", "a"], "e1", {"w": 1}) == A,
        "lonely_same": build([], "e1", node_attrs={"solo": {"color": "red"}})
        == build([], "e1", node_attrs={"solo": {"color": "red"}}),
        "diff_node_attr": build([], "e1", node_attrs={"solo": {"color": "red"}})
        == build([], "e1", node_attrs={"solo": {"color": "blue"}}),
    }


def v_copy_counter_preserved() -> dict:
    # Reviewer insurance: XGI's copy() carries the auto-id counter
    # (`cp._edge_uid = copy(self._edge_uid)`) — an auto edge added to the
    # copy gets the NEXT counter value, it does not restart at 0.
    H = xgi.Hypergraph()
    H.add_edge(["a"])  # auto id 0 — counter now at 1
    cp = H.copy()
    cp.add_edge(["b"])  # must get the next counter value, not 0
    return {
        "h_edge_ids": _ids(H),
        "cp_edge_ids": _ids(cp),
        "h_num_edges": H.num_edges,
        "cp_num_edges": cp.num_edges,
    }


def v_copy_independence() -> dict:
    H = xgi.Hypergraph()
    H.add_node("a", color="red")
    H.add_edge(["a", "b"], idx="e1", heat=0.5)
    H["name"] = "test"
    C = H.copy()
    # Mutate the ORIGINAL in every channel — node attrs, edge attrs, net
    # attrs, membership. H.copy() is a deep, independent clone: the copy
    # must be untouched by all of it.
    H.nodes["a"]["color"] = "blue"
    H.edges["e1"]["heat"] = 0.9
    H["name"] = "modified"
    H.add_node("c")
    return {
        "node_attrs": dict(C.nodes["a"]),
        "edge_attrs": dict(C.edges["e1"]),
        "net_name": C["name"],
        "num_nodes": C.num_nodes,
        "num_edges": C.num_edges,
        "has_c": "c" in C,
    }


def v_add_node_to_edge_autocreate() -> dict:
    # XGI's add_node_to_edge auto-creates a missing edge AND a missing node
    # (runtime-verified, matching its docstring), returns None, is idempotent
    # on re-add (set semantics), and preserves existing edge attrs.
    H = xgi.Hypergraph()
    ret_create = H.add_node_to_edge("new_edge", "new_node")  # both missing
    H.add_edge(["a", "b"], idx="e1", heat=0.5)
    H.add_node_to_edge("e1", "c")  # existing edge, new node
    ret_readd = H.add_node_to_edge("e1", "c")  # idempotent re-add
    H.add_node_to_edge("e1", "a")  # existing node into existing edge
    return {
        "return_create": ret_create,
        "return_readd": ret_readd,
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "node_ids": sorted(str(n) for n in H.nodes),
        "members": _members_sorted(H),
        "memberships": {str(n): sorted(str(e) for e in H.nodes.memberships(n)) for n in H.nodes},
        "edge_attrs_e1": dict(H.edges["e1"]),
    }


def v_add_node_to_edge_numeric_id_no_bump() -> dict:
    # XGI's add_node_to_edge NEVER touches _edge_uid — only add_edge calls
    # next(). Auto-creating a NUMERIC edge id via add_node_to_edge does not
    # bump the counter: the next auto id is 0, not 6. (And XGI's add_edge
    # does not existence-check its auto id, so add_node_to_edge(0, ...) then
    # add_edge(...) silently OVERWRITES edge 0's members in XGI — the Rust
    # core's D11 bump exists to foreclose exactly this collision class.)
    H = xgi.Hypergraph()
    H.add_node_to_edge(5, "x")
    H.add_edge(["y"])  # auto id — XGI counter untouched by add_node_to_edge
    return {"edge_ids": _ids(H), "members": _members_sorted(H)}


def v_remove_node_from_edge_keep_empty() -> dict:
    # remove_empty=False: the emptied edge SURVIVES (empty member set);
    # the node survives too.
    H = xgi.Hypergraph()
    H.add_edge(["a"], idx="e1")
    H.remove_node_from_edge("e1", "a", remove_empty=False)
    return {
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "members": _members_sorted(H),
        "memberships": {str(n): sorted(str(e) for e in H.nodes.memberships(n)) for n in H.nodes},
    }


def v_remove_node_from_edge_drop_empty() -> dict:
    # remove_empty=True (the XGI default): an edge left empty is removed;
    # the node survives (here still a member of e1).
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["b"], idx="e2")
    H.remove_node_from_edge("e2", "b")
    return {
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "num_nodes": H.num_nodes,
        "node_ids": sorted(str(n) for n in H.nodes),
        "members": _members_sorted(H),
        "memberships": {str(n): sorted(str(e) for e in H.nodes.memberships(n)) for n in H.nodes},
    }


def v_membership_errors() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): all three remove_node_from_edge error
    # branches raise XGIError (the D2 error-channel class), each with a
    # DISTINCT message: missing edge -> "Edge noedge not in the hypergraph";
    # missing node -> "Node ghost not in the hypergraph"; node not in edge
    # -> "Edge e1 does not contain node b". The Rust core maps each branch
    # to a dedicated MembershipError variant (EdgeNotFound / NodeNotFound /
    # NotAMember); the binding translates Err -> raise.
    out = {}
    H = xgi.Hypergraph()
    try:
        H.remove_node_from_edge("noedge", "a")
    except Exception as exc:  # recording the observed type IS the vector
        out["missing_edge"] = {"exception": type(exc).__name__, "message": str(exc)}
    H2 = xgi.Hypergraph()
    H2.add_edge(["a"], idx="e1")
    try:
        H2.remove_node_from_edge("e1", "ghost")
    except Exception as exc:
        out["missing_node"] = {"exception": type(exc).__name__, "message": str(exc)}
    H3 = xgi.Hypergraph()
    H3.add_edge(["a"], idx="e1")
    H3.add_node("b")
    try:
        H3.remove_node_from_edge("e1", "b")
    except Exception as exc:
        out["not_in_edge"] = {"exception": type(exc).__name__, "message": str(exc)}
    return out


def v_remove_node_remove_empty() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): remove_node(n, strong, remove_empty)
    # is THREE-mode. Weak + remove_empty=False leaves an emptied edge in
    # place (H.edges still lists it; members(e) == set()); weak +
    # remove_empty=True (the default) drops it. Strong mode removes every
    # incident edge REGARDLESS of remove_empty (probed with
    # remove_empty=False: e1/e2 still removed, e4 survives). All branches
    # return None.
    out = {}
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["b"], idx="e2")
    ret = H.remove_node("b", strong=False, remove_empty=False)
    out["weak_keep"] = {
        "return": ret,
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "node_ids": sorted(str(n) for n in H.nodes),
        "has_node_b": "b" in H,
        "members": _members_sorted(H),
    }
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["b"], idx="e2")
    H.remove_node("b", strong=False, remove_empty=True)
    out["weak_drop"] = {
        "edge_ids": _ids(H),
        "num_edges": H.num_edges,
        "members": _members_sorted(H),
    }
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["a", "c", "d"], idx="e2")
    H.add_edge(["c", "d"], idx="e4")
    H.remove_node("a", strong=True, remove_empty=False)
    out["strong_ignores_flag"] = {
        "edge_ids": _ids(H),
        "node_ids": sorted(str(n) for n in H.nodes),
        "members": _members_sorted(H),
    }
    return out


def v_remove_nodes_from_missing() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): remove_nodes_from WARNS on a missing
    # id ("Node ghost not in hypergraph" — note: NO "the", unlike
    # remove_node's IDNotFound message), SKIPS it, and CONTINUES with the
    # rest (c is still removed after ghost); returns None. The Rust core
    # records a per-item Err(NodeError::NotFound) and continues — the
    # D2-class channel translation; the binding warns per Err item.
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["b", "c"], idx="e2")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = H.remove_nodes_from(["b", "ghost", "c"])
    return {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_message": str(caught[0].message) if caught else None,
        "node_ids": sorted(str(n) for n in H.nodes),
        "edge_ids": _ids(H),
        "members": _members_sorted(H),
    }


def v_remove_edges_from_missing() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): remove_edges_from iterates in order
    # and RAISES IDNotFound("ID ghost not found") on the first missing id
    # — ids BEFORE it are already removed (partial effects); ids AFTER it
    # are never attempted (["e1", "ghost", "e3"] leaves e2 AND e3 in
    # place). An all-valid bunch returns None and removes every listed
    # edge (nodes survive). The Rust core records per-item results and
    # STOPS after the first Err — the D2-class channel translation — so
    # the binding can reproduce the raise exactly (state already matches).
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1")
    H.add_edge(["b", "c"], idx="e2")
    H.add_edge(["c", "d"], idx="e3")
    out = {}
    try:
        H.remove_edges_from(["e1", "ghost", "e3"])
    except Exception as exc:  # recording the observed type IS the vector
        out["exception"] = type(exc).__name__
        out["message"] = str(exc)
    out["edge_ids_after"] = _ids(H)
    out["num_nodes"] = H.num_nodes
    H2 = xgi.Hypergraph()
    H2.add_edge(["a", "b"], idx="e1")
    H2.add_edge(["b", "c"], idx="e2")
    out["all_valid_return"] = H2.remove_edges_from(["e1", "e2"])
    out["all_valid_edges"] = _ids(H2)
    out["all_valid_nodes"] = sorted(str(n) for n in H2.nodes)
    return out


def v_set_node_attributes_bulk() -> dict:
    # XGI's set_node_attributes(values, name=None) with a dict-of-dicts:
    # MERGES into each existing node's attr dict, and a missing node is
    # WARNED about ("Node ghost does not exist!") + SKIPPED — never
    # auto-created, never raises. A list-of-pairs input raises XGIError
    # ("Must pass a dictionary of dictionaries") — XGI is dict-of-dicts
    # only at the Python boundary (the Rust core takes pairs; D7 class).
    H = xgi.Hypergraph()
    H.add_node("a", x=1)
    H.add_node("b")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = H.set_node_attributes(
            {"a": {"color": "red"}, "b": {"color": "blue"}, "ghost": {"color": "green"}}
        )
    out = {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_message": str(caught[0].message) if caught else None,
        "attrs_a": dict(H.nodes["a"]),  # merged: x survives, color added
        "attrs_b": dict(H.nodes["b"]),
        "num_nodes": H.num_nodes,  # ghost NOT auto-created
    }
    H2 = xgi.Hypergraph()
    H2.add_node("a")
    try:
        H2.set_node_attributes([("a", {"k": "v"})])
    except Exception as exc:  # recording the observed type IS the vector
        out["pairs_exception"] = type(exc).__name__
        out["pairs_message"] = str(exc)
    return out


def v_set_edge_attributes_bulk() -> dict:
    # Same shape for edges: merge into existing edge attr dicts; a missing
    # edge id warns ("Edge ghost does not exist!") + skips; edge count and
    # membership untouched.
    H = xgi.Hypergraph()
    H.add_edge(["a"], idx="e1", w=1)
    H.add_edge(["b"], idx="e2")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = H.set_edge_attributes({"e1": {"heat": 0.5}, "ghost": {"x": 1}})
    return {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_message": str(caught[0].message) if caught else None,
        "attrs_e1": dict(H.edges["e1"]),  # merged: w survives, heat added
        "attrs_e2": dict(H.edges["e2"]),
        "num_edges": H.num_edges,
    }


def v_clear_edges_keeps_nodes_counter() -> dict:
    # XGI's clear_edges(): "Remove all edges from the graph without
    # altering any nodes." It clears _edge/_edge_attr and empties every
    # node's membership set; nodes, node attrs, and net attrs survive;
    # returns None. Like clear() (D10) it does NOT touch _edge_uid — the
    # next auto id continues the sequence (unlike D10 there is no
    # "cleared ≡ fresh" reading: the node state is preserved, so counter
    # continuity matches state continuity; the Rust core CONFORMS here).
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"])  # auto id 0 — bumps XGI's uid counter to 1
    H.add_edge(["c", "d"], idx="e1", heat=0.5)
    H.add_node("lonely", x=1)
    H["name"] = "test"
    ret = H.clear_edges()
    state = {
        "return": ret,
        "num_nodes": H.num_nodes,
        "num_edges": H.num_edges,
        "node_ids": sorted(str(n) for n in H.nodes),
        "edge_ids": _ids(H),
        "lonely_attrs": dict(H.nodes["lonely"]),
        "net_attrs": dict(H._net_attr),
        "memberships_a": sorted(str(e) for e in H.nodes.memberships("a")),
    }
    # Counter NOT reset: the next auto id is 1, continuing the sequence.
    H.add_edge(["z"])
    state["auto_ids_after_clear_edges"] = _ids(H)
    return state


def v_freeze_blocks_mutation() -> dict:
    # XGI's freeze() monkey-patches a fixed method list with a raiser
    # (`XGIError: Frozen higher-order network can't be modified`) and sets
    # `frozen = True`; is_frozen is a property over that attribute. The
    # guarded list: add_node(s)_from, remove_node(s)_from, add_edge(s)_from,
    # add_weighted_edges_from, remove_edge(s)_from, add_node_to_edge,
    # remove_node_from_edge, clear. NOT guarded (holes, probed live):
    # clear_edges (deletes every edge on a FROZEN network — divergence
    # D12, the Rust core guards it), set_node_attributes /
    # set_edge_attributes / net-attr set / private attr-dict writes (the
    # attr-dict channel — the Rust core matches XGI and leaves it open).
    # And because the freeze is per-instance swizzling, copy() of a frozen
    # network is NOT frozen (the fresh instance never gets the patch —
    # divergence D13; the Rust core's frozen flag is data and copy()
    # carries it).
    H = xgi.Hypergraph()
    H.add_edge(["a", "b"], idx="e1", w=1)
    was_frozen = H.is_frozen
    H.freeze()
    probes = [
        ("add_node", lambda: H.add_node("z")),
        ("add_edge", lambda: H.add_edge(["a"])),
        ("remove_node", lambda: H.remove_node("a")),
        ("remove_edge", lambda: H.remove_edge("e1")),
        ("add_node_to_edge", lambda: H.add_node_to_edge("e1", "c")),
        ("remove_node_from_edge", lambda: H.remove_node_from_edge("e1", "a")),
        ("clear", lambda: H.clear()),
        ("set_node_attributes", lambda: H.set_node_attributes({"a": {"k": 1}})),
        ("set_edge_attributes", lambda: H.set_edge_attributes({"e1": {"k": 1}})),
        # LAST: unguarded in XGI — it really does clear the frozen graph's
        # edges, so every probe above must run before it.
        ("clear_edges", lambda: H.clear_edges()),
    ]
    guarded = {}
    for name, fn in probes:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fn()
            guarded[name] = None  # no raise — NOT guarded
        except Exception as exc:  # recording the observed type IS the vector
            guarded[name] = {"exception": type(exc).__name__, "message": str(exc)}

    H2 = xgi.Hypergraph()
    H2.add_edge(["a"], idx="e1")
    H2.freeze()
    return {
        "is_frozen_before": was_frozen,
        "is_frozen_after": H.is_frozen,
        "guarded": guarded,
        "copy_of_frozen_is_frozen": H2.copy().is_frozen,
    }


def v_repr_format() -> dict:
    # XGI's __repr__ is f"{cls}({self.edges.members()})" — the class name
    # wrapping the Python repr of the edge-members LIST. Edge order in the
    # list is insertion order (stable); member order INSIDE each set is
    # set-iteration order — unstable across runs for string ids (hash
    # randomization: one graph reprs as Hypergraph([{'a', 'b', 'c'}, ...])
    # on one invocation and Hypergraph([{'b', 'c', 'a'}, ...]) on the
    # next). The members are therefore recorded SORTED per edge; the
    # replay asserts the Rust Debug's INSERTION-ordered members (cited
    # divergence D5: XGI returns unordered sets — Rust is strictly more
    # defined). Lonely nodes never appear (only edges' members do).
    H = xgi.Hypergraph()
    H.add_edge(["a", "b", "c"])
    H.add_edge(["b", "c"], idx="e1")
    H.add_node("lonely")
    empty = xgi.Hypergraph()
    lone_empty_edge = xgi.Hypergraph()
    lone_empty_edge.add_edge([])
    return {
        # Stable projections only — the raw member-bearing repr string is
        # unrecordable (set-order nondeterminism would break regeneration
        # determinism).
        "repr_prefix": repr(H)[:11],  # "Hypergraph("
        "members_sorted": [sorted(str(n) for n in H.edges.members(e)) for e in H.edges],
        "repr_empty": repr(empty),  # "Hypergraph([])"
        # XGI renders an empty member set with Python's set() artifact;
        # the Rust core formats braces uniformly ("{}") — same D5 class.
        "repr_lone_empty_edge": repr(lone_empty_edge),  # "Hypergraph([set()])"
    }


def _di_ids(DH: xgi.DiHypergraph) -> list:
    return list(DH.edges)


def _di_dimembers_sorted(DH: xgi.DiHypergraph) -> dict:
    return {
        str(e): {
            "tail": sorted(str(n) for n in DH.edges.tail(e)),
            "head": sorted(str(n) for n in DH.edges.head(e)),
        }
        for e in DH.edges
    }


def _di_members_sorted(DH: xgi.DiHypergraph) -> dict:
    return {str(e): sorted(str(n) for n in DH.edges.members(e)) for e in DH.edges}


def _di_dimemberships_sorted(DH: xgi.DiHypergraph) -> dict:
    # (in, out) tuple order — in = edges where n is in the HEAD, out =
    # edges where n is in the TAIL (probed: tail-only node -> (set(), {e}),
    # head-only node -> ({e}, set())).
    return {
        str(n): [
            sorted(str(e) for e in DH.nodes.dimemberships(n)[0]),
            sorted(str(e) for e in DH.nodes.dimemberships(n)[1]),
        ]
        for n in DH.nodes
    }


def v_di_add_edge_dimembers() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): add_edge((tail, head)) — tail is the
    # FIRST entry, head the SECOND; returns None. dimembers(e) =
    # (tail, head); members(e) = tail ∪ head. dimemberships(n) =
    # (in, out): "in" = edges where n is in the HEAD, "out" = edges where
    # n is in the TAIL — IN FIRST (probed on node 1, tail-only ->
    # (set(), {0}); node 4, head-only -> ({0}, set())).
    DH = xgi.DiHypergraph()
    ret = DH.add_edge(([1, 2, 3], [2, 3, 4]))
    return {
        "return": ret,
        "edge_ids": _di_ids(DH),
        "num_nodes": DH.num_nodes,
        "node_ids": sorted(str(n) for n in DH.nodes),
        "dimembers": _di_dimembers_sorted(DH),
        "members": _di_members_sorted(DH),
        "dimemberships": _di_dimemberships_sorted(DH),
        "memberships": {str(n): sorted(str(e) for e in DH.nodes.memberships(n)) for n in DH.nodes},
    }


def v_di_uid_counter() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): DiHypergraph shares
    # update_uid_counter with Hypergraph — auto ids are ints 0, 1; int idx
    # 5 bumps the next auto to 6; str idx "5" does NOT bump (next auto 0);
    # float idx 5.0 bumps (next auto 6); non-numeric str "x" does not.
    # (D3/D4 parity: the Rust core bumps iff idx.parse::<u64>() succeeds.)
    out = {}
    DH = xgi.DiHypergraph()
    DH.add_edge(([1], [2]))
    DH.add_edge(([3], [4]))
    DH.add_edge(([5], [6]), idx=5)
    DH.add_edge(([7], [8]))
    out["int_idx_bumps"] = _di_ids(DH)
    DH = xgi.DiHypergraph()
    DH.add_edge(([1], [2]), idx="5")
    DH.add_edge(([3], [4]))
    out["str_idx_no_bump"] = _di_ids(DH)
    DH = xgi.DiHypergraph()
    DH.add_edge(([1], [2]), idx=5.0)
    DH.add_edge(([3], [4]))
    out["float_idx_bumps"] = _di_ids(DH)
    DH = xgi.DiHypergraph()
    DH.add_edge(([1], [2]), idx="x")
    DH.add_edge(([3], [4]))
    out["nonnumeric_idx_no_bump"] = _di_ids(DH)
    return out


def v_di_dup_idx() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): duplicate idx warns
    # ("uid e1 already exists, cannot add edge ([3], [4])") + no-ops,
    # returns None — the D2 class. The dup's members are never added.
    DH = xgi.DiHypergraph()
    DH.add_edge(([1], [2]), idx="e1")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = DH.add_edge(([3], [4]), idx="e1")
    return {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_prefix": str(caught[0].message)[:22] if caught else None,
        "edge_ids": _di_ids(DH),
        "num_edges": DH.num_edges,
        "num_nodes": DH.num_nodes,
        "dimembers": _di_dimembers_sorted(DH),
    }


def v_di_empty_edge() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): add_edge(([], [])) creates an empty
    # directed edge — dimembers (set(), set()) — returns None; an
    # empty-tail-only or empty-head-only edge is likewise allowed. D1-class
    # parity with the undirected add_edge([]).
    out = {}
    DH = xgi.DiHypergraph()
    ret = DH.add_edge(([], []))
    out["both_empty"] = {
        "return": ret,
        "edge_ids": _di_ids(DH),
        "num_edges": DH.num_edges,
        "num_nodes": DH.num_nodes,
        "dimembers": _di_dimembers_sorted(DH),
    }
    DH = xgi.DiHypergraph()
    DH.add_edge(([], [1]))
    out["empty_tail"] = {"dimembers": _di_dimembers_sorted(DH)}
    DH = xgi.DiHypergraph()
    DH.add_edge(([1], []))
    out["empty_head"] = {"dimembers": _di_dimembers_sorted(DH)}
    return out


def v_di_both_directions() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): a node listed in BOTH the tail and
    # the head of the same edge is stored in both sets and survives
    # round-trip — dimembers shows it in both, dimemberships lists the
    # edge in both slots. Duplicate members within one direction are
    # deduped (set semantics per direction).
    DH = xgi.DiHypergraph()
    DH.add_edge(([1, 1, 2], [2, 2, 3]), idx="e1")
    return {
        "dimembers": _di_dimembers_sorted(DH),
        "members": _di_members_sorted(DH),
        "dimemberships": _di_dimemberships_sorted(DH),
        "num_nodes": DH.num_nodes,
    }


def v_di_members_must_be_pair() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): add_edge with non-list/tuple members
    # raises XGIError "Directed edge must be a list or tuple!" (a set or a
    # string hits it; a list of ints PASSES the isinstance check and dies
    # iterating — TypeError "'int' object is not iterable", also pinned).
    # add_node_to_edge with an invalid direction string raises XGIError
    # "Invalid direction!". Divergence D14: the Rust core makes BOTH
    # compile-time-impossible — add_edge takes (Vec<String>, Vec<String>)
    # and direction is the Direction enum; the Phase 7 binding exposes
    # shims raising XGIError for conformance.
    out = {}
    DH = xgi.DiHypergraph()
    try:
        DH.add_edge({1, 2, 3})  # a set — not a list/tuple
    except Exception as exc:  # recording the observed type IS the vector
        out["set_members"] = {"exception": type(exc).__name__, "message": str(exc)}
    try:
        DH.add_edge("abc")  # a string — not a list/tuple
    except Exception as exc:
        out["str_members"] = {"exception": type(exc).__name__, "message": str(exc)}
    try:
        DH.add_edge([1, 2, 3])  # list of ints — passes isinstance, dies iterating
    except Exception as exc:
        out["int_list_members"] = {"exception": type(exc).__name__, "message": str(exc)}
    DH2 = xgi.DiHypergraph()
    DH2.add_edge(([1], [2]), idx="e1")
    try:
        DH2.add_node_to_edge("e1", 3, "sideways")
    except Exception as exc:
        out["invalid_direction"] = {"exception": type(exc).__name__, "message": str(exc)}
    return out


def v_di_add_node_to_edge() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): direction "in" puts the node in the
    # TAIL (_edge[e]["in"]), "out" in the HEAD. Auto-creates a missing
    # edge AND a missing node; returns None; set semantics — re-adding the
    # same (node, direction) is a no-op, and adding the same node in the
    # OTHER direction puts it in BOTH sets. D11-extension: DiHypergraph's
    # add_node_to_edge does NOT call update_uid_counter either — after
    # auto-creating numeric edge 5, the next auto id is 0 (the same
    # silent-overwrite footgun as undirected D11: XGI's auto-id add_edge
    # does not existence-check, so the sequence OVERWRITES edge 0's
    # members; pinned below). The Rust core bumps iff the id parses as
    # u64, extending the D3/D11 rule to DiHypergraph.
    DH = xgi.DiHypergraph()
    ret_in = DH.add_node_to_edge("newedge", "newnode", "in")
    ret_out = DH.add_node_to_edge("e2", "n2", "out")
    DH.add_edge(([1], [2]), idx="e1")
    DH.add_node_to_edge("e1", 1, "in")  # re-add same direction: no-op
    DH.add_node_to_edge("e1", 1, "out")  # other direction: node in BOTH
    out = {
        "return_in": ret_in,
        "return_out": ret_out,
        "edge_ids": _di_ids(DH),
        "num_nodes": DH.num_nodes,
        "node_ids": sorted(str(n) for n in DH.nodes),
        "dimembers": _di_dimembers_sorted(DH),
        "dimemberships": _di_dimemberships_sorted(DH),
    }
    DH2 = xgi.DiHypergraph()
    DH2.add_node_to_edge(5, "x", "in")
    DH2.add_edge(([1], [2]))  # auto id — XGI counter untouched
    out["numeric_id_no_bump"] = {
        "edge_ids": _di_ids(DH2),
        "dimembers": _di_dimembers_sorted(DH2),
    }
    return out


def v_di_remove_node_from_edge() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): removes ONLY the direction's side —
    # removing node 2 with direction "in" (tail) from ([1,2],[2,3]) leaves
    # 2 in the HEAD. Directed "emptied" = BOTH tail AND head empty:
    # removing the last tail member of ([1],[2]) with remove_empty=True
    # leaves the edge ALIVE (head still has 2); removing the last head
    # member then empties it and it IS dropped. remove_empty=False keeps a
    # both-empty edge. Errors (XGIError, D2 channel): missing edge
    # "Edge noedge not in the hypergraph"; missing node "Node ghost not in
    # the hypergraph"; not-a-member is PER-DIRECTION:
    # "in-edge e1 does not contain node b" / "out-edge e1 does not contain
    # node b" (a head-only member fails direction "in"). Invalid direction
    # is validated FIRST, before the existence checks — D14 makes it
    # compile-time-impossible in Rust.
    out = {}
    DH = xgi.DiHypergraph()
    DH.add_edge(([1, 2], [2, 3]), idx="e1")
    DH.remove_node_from_edge("e1", 2, "in", remove_empty=False)
    out["direction_only"] = {
        "dimembers": _di_dimembers_sorted(DH),
        "dimemberships": _di_dimemberships_sorted(DH),
        "edge_ids": _di_ids(DH),
        "node_ids": sorted(str(n) for n in DH.nodes),
    }
    DH2 = xgi.DiHypergraph()
    DH2.add_edge(([1], [2]), idx="e2")
    DH2.remove_node_from_edge("e2", 1, "in")  # remove_empty=True default
    out["empty_means_both_sides"] = {
        "edge_ids": _di_ids(DH2),
        "dimembers": _di_dimembers_sorted(DH2),
    }
    DH2.remove_node_from_edge("e2", 2, "out")
    out["both_empty_dropped"] = {
        "edge_ids": _di_ids(DH2),
        "node_ids": sorted(str(n) for n in DH2.nodes),
    }
    DH3 = xgi.DiHypergraph()
    DH3.add_edge(([1], []), idx="e3")
    DH3.remove_node_from_edge("e3", 1, "in", remove_empty=False)
    out["keep_empty"] = {
        "edge_ids": _di_ids(DH3),
        "dimembers": _di_dimembers_sorted(DH3),
    }
    errs = {}
    DH4 = xgi.DiHypergraph()
    try:
        DH4.remove_node_from_edge("noedge", "a", "in")
    except Exception as exc:  # recording the observed type IS the vector
        errs["missing_edge"] = {"exception": type(exc).__name__, "message": str(exc)}
    DH4.add_edge(([1], [2]), idx="e1")
    try:
        DH4.remove_node_from_edge("e1", "ghost", "in")
    except Exception as exc:
        errs["missing_node"] = {"exception": type(exc).__name__, "message": str(exc)}
    DH4.add_node("b")
    try:
        DH4.remove_node_from_edge("e1", "b", "in")
    except Exception as exc:
        errs["not_in_tail"] = {"exception": type(exc).__name__, "message": str(exc)}
    try:
        DH4.remove_node_from_edge("e1", "b", "out")
    except Exception as exc:
        errs["not_in_head"] = {"exception": type(exc).__name__, "message": str(exc)}
    try:
        DH4.remove_node_from_edge("e1", 2, "in")  # head-only member, wrong direction
    except Exception as exc:
        errs["wrong_direction_member"] = {
            "exception": type(exc).__name__,
            "message": str(exc),
        }
    out["errors"] = errs
    return out


def v_di_remove_node_modes() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): remove_node(n, strong, remove_empty)
    # — weak drops the node from BOTH directions of every containing edge;
    # an edge left with BOTH tail and head empty is removed iff
    # remove_empty (an edge with one side still populated SURVIVES — e2
    # below keeps (set(), {4})). Strong removes every incident edge
    # (in ∪ out) ENTIRELY, regardless of remove_empty. Missing node:
    # IDNotFound "ID ghost not found". remove_nodes_from WARNS
    # "Node ghost not in dihypergraph" (note: "dihypergraph", unlike the
    # undirected "hypergraph"), SKIPS, CONTINUES. remove_edges_from RAISES
    # IDNotFound mid-iteration (partial effects: e1 already removed, e3
    # never attempted). remove_edge on a missing id: IDNotFound.
    out = {}
    DH = xgi.DiHypergraph()
    DH.add_edge(([1, 2], [2, 3]), idx="e1")
    DH.add_edge(([2], [4]), idx="e2")
    DH.add_edge(([5], [2]), idx="e3")
    ret = DH.remove_node(2, strong=False, remove_empty=False)
    out["weak_keep"] = {
        "return": ret,
        "edge_ids": _di_ids(DH),
        "node_ids": sorted(str(n) for n in DH.nodes),
        "has_node_2": 2 in DH,
        "dimembers": _di_dimembers_sorted(DH),
    }
    DH2 = xgi.DiHypergraph()
    DH2.add_edge(([2], [4]), idx="e2")
    DH2.add_edge(([2], []), idx="e5")
    DH2.remove_node(2)  # XGI defaults: strong=False, remove_empty=True
    out["weak_drop"] = {
        "edge_ids": _di_ids(DH2),
        "dimembers": _di_dimembers_sorted(DH2),
    }
    DH3 = xgi.DiHypergraph()
    DH3.add_edge(([1, 2], [3]), idx="e1")
    DH3.add_edge(([4], [2, 5]), idx="e2")
    DH3.add_edge(([6], [7]), idx="e4")
    DH3.remove_node(2, strong=True, remove_empty=False)
    out["strong_ignores_flag"] = {
        "edge_ids": _di_ids(DH3),
        "node_ids": sorted(str(n) for n in DH3.nodes),
        "dimembers": _di_dimembers_sorted(DH3),
    }
    DH4 = xgi.DiHypergraph()
    try:
        DH4.remove_node("ghost")
    except Exception as exc:  # recording the observed type IS the vector
        out["missing_node"] = {"exception": type(exc).__name__, "message": str(exc)}
    DH5 = xgi.DiHypergraph()
    DH5.add_edge(([1, 2], [3]), idx="e1")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = DH5.remove_nodes_from([1, "ghost", 2])
    out["nodes_from_missing"] = {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_message": str(caught[0].message) if caught else None,
        "node_ids": sorted(str(n) for n in DH5.nodes),
        "edge_ids": _di_ids(DH5),
        "dimembers": _di_dimembers_sorted(DH5),
    }
    DH6 = xgi.DiHypergraph()
    DH6.add_edge(([1], [2]), idx="e1")
    DH6.add_edge(([2], [3]), idx="e2")
    DH6.add_edge(([3], [4]), idx="e3")
    edges_from = {}
    try:
        DH6.remove_edges_from(["e1", "ghost", "e3"])
    except Exception as exc:  # recording the observed type IS the vector
        edges_from["exception"] = type(exc).__name__
        edges_from["message"] = str(exc)
    edges_from["edge_ids_after"] = _di_ids(DH6)
    out["edges_from_missing"] = edges_from
    DH7 = xgi.DiHypergraph()
    try:
        DH7.remove_edge("ghost")
    except Exception as exc:  # recording the observed type IS the vector
        out["remove_edge_missing"] = {
            "exception": type(exc).__name__,
            "message": str(exc),
        }
    return out


def v_di_repr() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): __repr__ is
    # f"{cls}({self.edges.dimembers()})" — the class name wrapping the
    # dimembers LIST: one (tail, head) set-tuple per edge, edges in
    # insertion order (stable); member order INSIDE each set is
    # hash-ordered (unstable across runs for str ids) — recorded SORTED
    # per side. An empty side renders with Python's set() artifact; a
    # lonely node never appears (only edges' members do). The Rust Debug
    # formats both sides with uniform braces and insertion-ordered
    # members (D5 class — strictly more defined).
    DH = xgi.DiHypergraph()
    DH.add_edge((["a", "b", "c"], ["b", "d"]))
    DH.add_edge((["a"], []), idx="e1")
    DH.add_node("lonely")
    empty = xgi.DiHypergraph()
    both_empty = xgi.DiHypergraph()
    both_empty.add_edge(([], []))
    return {
        "repr_prefix": repr(DH)[:13],  # "DiHypergraph("
        "dimembers_sorted": [
            [
                sorted(str(n) for n in DH.edges.tail(e)),
                sorted(str(n) for n in DH.edges.head(e)),
            ]
            for e in DH.edges
        ],
        "repr_empty": repr(empty),  # "DiHypergraph([])"
        # XGI renders an empty side with the set() artifact; the Rust
        # core formats braces uniformly ("{}") — same D5 class.
        "repr_both_empty_edge": repr(both_empty),  # "DiHypergraph([(set(), set())])"
    }


def v_di_eq() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): DiHypergraph.__eq__ delegates to
    # xgi.algorithms.equal with the defaults (compare_edge_ids=True,
    # compare_attrs=True). equal compares H1._edge != H2._edge — for
    # DiHypergraph that mapping is {id: {"in": tail_set, "out":
    # head_set}} — so DIRECTION IS SIGNIFICANT: the same nodes with
    # tail/head swapped are NOT equal; a node in BOTH directions differs
    # from a tail-only node. Node attrs are significant (every node
    # carries an attr dict — a lonely node with EMPTY attrs still
    # differs from an absent one), edge attrs and net attrs are
    # significant; member order is not.
    def build(edge, edge_attr=None, node_attrs=None, net=None):
        members, idx = edge
        DH = xgi.DiHypergraph()
        DH.add_edge(members, idx=idx, **(edge_attr or {}))
        for n, a in (node_attrs or {}).items():
            if n in DH:
                DH.nodes[n].update(a)
            else:
                DH.add_node(n, **a)
        for k, val in (net or {}).items():
            DH[k] = val
        return DH

    A = build(((["a", "b"], ["c"]), "e1"))
    return {
        "same": build(((["a", "b"], ["c"]), "e1")) == A,
        "direction_flipped": build(((["c"], ["a", "b"]), "e1")) == A,
        "member_order_insignificant": build(((["b", "a"], ["c"]), "e1")) == A,
        "diff_edge_id": build(((["a", "b"], ["c"]), "e2")) == A,
        "diff_edge_attr": build(((["a", "b"], ["c"]), "e1"), {"w": 2})
        == build(((["a", "b"], ["c"]), "e1"), {"w": 1}),
        "lonely_same": build(((["a", "b"], ["c"]), "e1"), None, {"solo": {"color": "red"}})
        == build(((["a", "b"], ["c"]), "e1"), None, {"solo": {"color": "red"}}),
        "diff_node_attr": build(((["a", "b"], ["c"]), "e1"), None, {"solo": {"color": "red"}})
        == build(((["a", "b"], ["c"]), "e1"), None, {"solo": {"color": "blue"}}),
        "lonely_missing": build(((["a", "b"], ["c"]), "e1"))
        == build(((["a", "b"], ["c"]), "e1"), None, {"solo": {"color": "red"}}),
        "diff_net_attr": build(((["a", "b"], ["c"]), "e1"), {"w": 1}, None, {"name": "x"})
        == build(((["a", "b"], ["c"]), "e1"), {"w": 1}),
        "both_vs_tail_only": build(((["a", "b"], ["b"]), "e1")) == build(((["a", "b"], []), "e1")),
        "empty_attr_lonely_vs_absent": build(((["a", "b"], ["c"]), "e1"), None, {"solo": {}})
        == build(((["a", "b"], ["c"]), "e1")),
    }


def v_di_add_edges_from() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): formats — (members) with auto ids;
    # (members, idx); (members, attrdict) with auto ids; (members, idx,
    # attrdict); dict {idx: members}; returns None. `**attr` broadcast
    # merges into EVERY edge with per-edge attrs taking precedence. A
    # dup idx warns ("uid e1 already exists, cannot add edge ([3],
    # [4]).") and CONTINUES (D2 class — the dup's members are never
    # added). The Notes claim empty edges are skipped — the runtime
    # CREATES an empty edge for ([], []) (D1-class docstring lie). The
    # Rust core takes uniform (tail, head, idx, attrs) quadruples —
    # format detection and broadcast merging are binding concerns (D7
    # class); per-edge results carry the dup as Err(AlreadyExists).
    out = {}
    DH = xgi.DiHypergraph()
    ret = DH.add_edges_from(
        [
            (  # format 1: members only, auto ids
                (["a", "b"], ["c"])
            ),
            (["d"], ["e", "f"]),
        ]
    )
    out["members_only"] = {
        "return": ret,
        "edge_ids": _di_ids(DH),
        "dimembers": _di_dimembers_sorted(DH),
    }
    DH = xgi.DiHypergraph()
    DH.add_edges_from(  # format 4: (members, idx, attrdict)
        [
            ((["a"], ["b"]), "one", {"color": "red"}),
            ((["c"], []), "two", {"color": "blue", "age": 40}),
        ]
    )
    out["with_idx_attrs"] = {
        "edge_ids": _di_ids(DH),
        "attrs": {str(e): dict(DH.edges[e]) for e in DH.edges},
        "dimembers": _di_dimembers_sorted(DH),
    }
    DH = xgi.DiHypergraph()
    DH.add_edges_from(  # broadcast: per-edge color wins, size merges in
        [((["a"], ["b"]), {"color": "red"})], color="blue", size=10
    )
    out["broadcast"] = {str(e): dict(DH.edges[e]) for e in DH.edges}
    DH = xgi.DiHypergraph()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = DH.add_edges_from(
            [
                ((["a"], ["b"]), "e1"),
                ((["c"], ["d"]), "e1"),  # dup — warns, skipped, members never added
                ((["e"], ["f"]), "e2"),
            ]
        )
    out["dup_warns_continues"] = {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_prefix": str(caught[0].message)[:22] if caught else None,
        "edge_ids": _di_ids(DH),
        "num_nodes": DH.num_nodes,
        "dimembers": _di_dimembers_sorted(DH),
    }
    DH = xgi.DiHypergraph()
    DH.add_edges_from([([], []), (["a"], ["b"])])
    out["empty_created"] = {
        "edge_ids": _di_ids(DH),
        "dimembers": _di_dimembers_sorted(DH),
    }
    return out


def v_di_set_attrs() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): set_node_attributes mirrors the
    # undirected class exactly — dict-of-dicts MERGES into each existing
    # node's attr dict; a missing node warns ("Node ghost does not
    # exist!") + SKIPS, never auto-created; a list of pairs raises
    # XGIError ("Must pass a dictionary of dictionaries"); scalar +
    # name= broadcasts to ALL nodes; dict-of-scalars + name= sets per
    # node (missing warns + skips). set_edge_attributes dict-of-dicts:
    # merge; a missing edge warns ("Edge ghost does not exist!") +
    # skips. The Rust core takes (id, attr_map) pairs — the scalar/name=
    # forms are binding sugar (D7 class); the warn channel is binding
    # (D2 class).
    out = {}
    DH = xgi.DiHypergraph()
    DH.add_edge((["a", "b"], ["c"]), idx="e1")
    DH.nodes["a"].update({"x": 1})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = DH.set_node_attributes(
            {"a": {"color": "red"}, "b": {"color": "blue"}, "ghost": {"color": "green"}}
        )
    out["node_dict_of_dicts"] = {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_message": str(caught[0].message) if caught else None,
        "attrs_a": dict(DH.nodes["a"]),  # merged: x survives, color added
        "attrs_b": dict(DH.nodes["b"]),
        "num_nodes": DH.num_nodes,  # ghost NOT auto-created
    }
    DH2 = xgi.DiHypergraph()
    DH2.add_node("a")
    try:
        DH2.set_node_attributes([("a", {"k": "v"})])
    except Exception as exc:  # recording the observed type IS the vector
        out["node_pairs_exception"] = type(exc).__name__
        out["node_pairs_message"] = str(exc)
    DH3 = xgi.DiHypergraph()
    DH3.add_edge((["a", "b"], ["c"]), idx="e1")
    DH3.set_node_attributes("red", name="color")
    out["node_scalar_broadcast"] = {
        "attrs_a": dict(DH3.nodes["a"]),
        "attrs_c": dict(DH3.nodes["c"]),
    }
    DH4 = xgi.DiHypergraph()
    DH4.add_edge((["a", "b"], ["c"]), idx="e1")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        DH4.set_node_attributes({"a": "red", "ghost": "green"}, name="color")
    out["node_dict_of_scalars"] = {
        "warned": len(caught) > 0,
        "warning_message": str(caught[0].message) if caught else None,
        "attrs_a": dict(DH4.nodes["a"]),
        "attrs_b": dict(DH4.nodes["b"]),
    }
    DH5 = xgi.DiHypergraph()
    DH5.add_edge((["a"], ["b"]), idx="e1", w=1)
    DH5.add_edge((["c"], ["d"]), idx="e2")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = DH5.set_edge_attributes({"e1": {"heat": 0.5}, "ghost": {"x": 1}})
    out["edge_dict_of_dicts"] = {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_message": str(caught[0].message) if caught else None,
        "attrs_e1": dict(DH5.edges["e1"]),  # merged: w survives, heat added
        "attrs_e2": dict(DH5.edges["e2"]),
        "num_edges": DH5.num_edges,
    }
    return out


def v_di_clear_freeze() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): clear() empties nodes, edges, all
    # attr channels, and net attrs — and, like the undirected class
    # (D10), does NOT reset _edge_uid (the next auto id continues at 1;
    # the Rust core resets — clear() ≡ new()). freeze() guards
    # add_node(s)_from, add_edge(s)_from, remove_node(s)_from,
    # remove_edge(s)_from, and clear — and, UNLIKE the undirected class,
    # NOT add_node_to_edge / remove_node_from_edge (both mutate a FROZEN
    # DiHypergraph unimpeded — the Rust core guards ALL structural
    # mutators uniformly; D12 extension, Task 4 already landed the
    # guard). clear_edges DOES NOT EXIST on DiHypergraph (AttributeError
    # via XGI's __getattr__ stat fallback — the Rust core provides it
    # for API uniformity; D16). The attr-dict channel
    # (set_node_attributes / set_edge_attributes) is unguarded, matching
    # the undirected class. copy() of a frozen DiHypergraph is NOT
    # frozen (D13 parity — the Rust core's flag is data, carried).
    DH = xgi.DiHypergraph()
    DH.add_edge((["a", "b"], ["c"]))  # auto id 0 — bumps XGI's counter
    DH.add_edge((["d"], ["e"]), idx="e1", heat=0.5)
    DH.add_node("lonely", x=1)
    DH["name"] = "test"
    DH.clear()
    out = {
        "clear": {
            "num_nodes": DH.num_nodes,
            "num_edges": DH.num_edges,
            "node_ids": sorted(str(n) for n in DH.nodes),
            "edge_ids": _di_ids(DH),
            "net_attrs": dict(DH._net_attr),
        }
    }
    DH.add_edge((["z"], []))
    out["clear"]["auto_ids_after_clear"] = _di_ids(DH)

    DH = xgi.DiHypergraph()
    DH.add_edge((["a", "b"], ["c"]), idx="e1", w=1)
    was_frozen = DH.is_frozen
    DH.freeze()
    probes = [
        ("add_node", lambda: DH.add_node("z")),
        ("add_nodes_from", lambda: DH.add_nodes_from(["z"])),
        ("add_edge", lambda: DH.add_edge((["a"], ["b"]))),
        ("add_edges_from", lambda: DH.add_edges_from([(["a"], ["b"])])),
        ("remove_node", lambda: DH.remove_node("a")),
        ("remove_nodes_from", lambda: DH.remove_nodes_from(["a"])),
        ("remove_edge", lambda: DH.remove_edge("e1")),
        ("remove_edges_from", lambda: DH.remove_edges_from(["e1"])),
        ("add_node_to_edge", lambda: DH.add_node_to_edge("e1", "n", "in")),
        ("remove_node_from_edge", lambda: DH.remove_node_from_edge("e1", "a", "in")),
        ("clear", lambda: DH.clear()),
        ("set_node_attributes", lambda: DH.set_node_attributes({"a": {"k": 1}})),
        ("set_edge_attributes", lambda: DH.set_edge_attributes({"e1": {"k": 1}})),
        # LAST in spirit: not a method at all — AttributeError, not a
        # guard outcome. Runs after the mutation-capable unguarded
        # probes above; each probe records raise/no-raise only.
        ("clear_edges", lambda: DH.clear_edges()),
    ]
    guarded = {}
    for name, fn in probes:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fn()
            guarded[name] = None  # no raise — NOT guarded
        except Exception as exc:  # recording the observed type IS the vector
            guarded[name] = {"exception": type(exc).__name__, "message": str(exc)}

    DH2 = xgi.DiHypergraph()
    DH2.add_edge((["a"], ["b"]))
    DH2.freeze()
    out["freeze"] = {
        "is_frozen_before": was_frozen,
        "is_frozen_after": DH.is_frozen,
        "guarded": guarded,
        "copy_of_frozen_is_frozen": DH2.copy().is_frozen,
    }
    return out


def _sc_members_sorted(S: xgi.SimplicialComplex) -> dict:
    return {str(e): sorted(str(n) for n in S.edges.members(e)) for e in S.edges}


def v_sc_add_simplex_closure() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): add_simplex([1,2,3]) creates the
    # top simplex FIRST (auto id 0), then its subfaces — EXACTLY the
    # proper non-empty subsets of sizes 2..n-1 (NO singletons, per the
    # doctest and runtime) — consuming auto ids in set(faces) iteration
    # order. That order is deterministic for INT members (pinned here)
    # but hash-dependent for str members; the Rust core enumerates
    # combinations in a canonical order (sizes n-1 down to 2,
    # lexicographic by member position) — the face-id -> member-set
    # mapping therefore differs from XGI's while the face SET is
    # identical (D5 class: strictly more defined). A 4-simplex yields
    # 1 + C(4,3) + C(4,2) = 11 edges. A 2-simplex adds NO subfaces.
    # An explicit str idx does not bump the counter (faces take 0,1,2);
    # an int idx bumps (faces take 11,12,13 after idx=10) — D3 parity:
    # the Rust core bumps iff the id parses as u64. add_simplex returns
    # None in every branch (D8 class).
    out = {}
    S = xgi.SimplicialComplex()
    ret = S.add_simplex([1, 2, 3])
    out["three"] = {
        "return": ret,
        "edge_ids": list(S.edges),
        "members": _sc_members_sorted(S),
    }
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2, 3, 4])
    out["four"] = {"edge_ids": list(S.edges), "members": _sc_members_sorted(S)}
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2])
    out["two"] = {"edge_ids": list(S.edges), "members": _sc_members_sorted(S)}
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2, 3], idx="top")
    out["str_idx_no_bump"] = {
        "edge_ids": list(S.edges),
        "members": _sc_members_sorted(S),
    }
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2, 3], idx=10)
    out["int_idx_bumps"] = {"edge_ids": list(S.edges), "members": _sc_members_sorted(S)}
    return out


def v_sc_redundant_simplex() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): re-adding the same member SET is a
    # SILENT no-op — no warning, returns None, num_edges unchanged. The
    # has_simplex member-set check precedes the dup-idx check, so even a
    # NEW explicit idx on an existing member set is silently discarded
    # (the idx is NOT consumed). Adding an existing subface ([1,2] after
    # [1,2,3]) is likewise a silent no-op. The Rust core returns
    # Ok(id-of-existing-edge) — the D8 return-channel class (XGI's None
    # cannot report the id).
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2, 3])
    out: dict = {"num_edges_before": S.num_edges}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = S.add_simplex([3, 2, 1])
    out["reorder"] = {
        "return": ret,
        "warned": len(caught) > 0,
        "num_edges": S.num_edges,
        "edge_ids": list(S.edges),
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = S.add_simplex([3, 2, 1], idx="newid")
    out["reorder_new_idx"] = {
        "return": ret,
        "warned": len(caught) > 0,
        "num_edges": S.num_edges,
        "edge_ids": list(S.edges),
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = S.add_simplex([1, 2])
    out["existing_face"] = {
        "return": ret,
        "warned": len(caught) > 0,
        "num_edges": S.num_edges,
        "edge_ids": list(S.edges),
    }
    return out


def v_sc_dup_idx() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): a dup idx with DIFFERENT members
    # warns ("uid s1 already exists, cannot add simplex frozenset({4,
    # 5})") + no-ops, returns None — the D2 class; the dup's members are
    # never added. (Contrast v_sc_redundant_simplex: same member set
    # short-circuits BEFORE the idx check, silently.)
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2, 3], idx="s1")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ret = S.add_simplex([4, 5], idx="s1")
    return {
        "return": ret,
        "warned": len(caught) > 0,
        "warning_prefix": str(caught[0].message)[:22] if caught else None,
        "edge_ids": list(S.edges),
        "num_nodes": S.num_nodes,
        "num_edges": S.num_edges,
        "members": _sc_members_sorted(S),
    }


def v_sc_empty_simplex() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): the Notes claim "currently cannot
    # add empty simplices" — the runtime CREATES an empty simplex (auto
    # id 0, no members; num_nodes 0, num_edges 1). A second
    # add_simplex([]) is a silent no-op (has_simplex([]) becomes True
    # once the empty edge exists). D1-class docstring lie — the Rust
    # core conforms to the runtime.
    S = xgi.SimplicialComplex()
    ret = S.add_simplex([])
    out = {
        "return": ret,
        "edge_ids": list(S.edges),
        "num_nodes": S.num_nodes,
        "num_edges": S.num_edges,
        "members": _sc_members_sorted(S),
        "has_empty": S.has_simplex([]),
    }
    ret2 = S.add_simplex([])
    out["again"] = {"return": ret2, "num_edges": S.num_edges, "edge_ids": list(S.edges)}
    return out


def v_sc_attrs_no_propagate() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): simplex attrs land ONLY on the top
    # simplex; every subface gets the empty attr dict (the docstring's
    # "attributes do not propagate to the subfaces" is runtime-true).
    # The Rust core gives faces E::default() — for the Value channel
    # that is Null, the core's empty-attrs placeholder ≈ XGI's {} (the
    # same convention as auto-created nodes; D7 class).
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2, 3], color="red")
    return {"attrs": {str(e): dict(S.edges[e]) for e in S.edges}}


def v_sc_has_simplex() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): member-SET comparison — [2,1]
    # matches {1,2}; a face added by closure matches; a non-member set
    # does not. (Note the constructor's closure: the [2,3,4] simplex
    # added faces [2,3], [2,4], [3,4] but NOT singletons.)
    S = xgi.SimplicialComplex([[1, 2], [2, 3, 4]])
    return {
        "reordered": S.has_simplex([2, 1]),
        "missing_set": S.has_simplex({1, 3}),
        "top": S.has_simplex([2, 3, 4]),
        "closure_face": S.has_simplex([2, 3]),
        "no_singletons": S.has_simplex([2]),
    }


def v_sc_falsy_idx_is_auto() -> dict:
    # PROBE (2026-07-18, xgi 0.10.2): add_simplex's idx handling is
    # `next(_edge_uid) if not idx else idx` — a FALSY idx (0, "") is
    # treated as ABSENT and replaced by an auto id (unique to
    # SimplicialComplex: Hypergraph and DiHypergraph test `idx is
    # None`). Divergence D17: the Rust core's Option<String> is exact —
    # Some("0") is an explicit id, None is auto. After add_simplex([1,
    # 2, 3], idx=5) the counter is 9 (top 5, faces 6..8), so a
    # subsequent add_simplex([4, 5], idx=0) landing at id 9 proves the
    # auto replacement.
    S = xgi.SimplicialComplex()
    S.add_simplex([1, 2, 3], idx=5)
    out = {"after_int_idx": list(S.edges)}
    S.add_simplex([4, 5], idx=0)
    out["zero_idx_edges"] = list(S.edges)
    S2 = xgi.SimplicialComplex()
    S2.add_simplex([1, 2], idx="")
    out["empty_str_idx_edges"] = list(S2.edges)
    return out


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
