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
