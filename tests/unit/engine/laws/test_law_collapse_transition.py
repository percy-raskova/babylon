"""Behavioral laws for CollapseTransitionSystem (P27 Phase-0 coverage
backfill, Task 11).

Read end-to-end before writing:
``src/babylon/engine/systems/collapse_transition.py`` (``step``, lines
59-104; ``_collapse_sovereign``, lines 106-201; ``_cleanup_orphaned_
sovereigns``, lines 276-290), plus the coefficient it stamps onto every
post-collapse CLAIMS edge,
``src/babylon/config/defines/balkanization.py::BalkanizationDefines.
initial_post_collapse_control_level`` (lines 135-140, default 0.8, bounded
``[0.0, 1.0]``), and the real graph query used to verify partition
exclusivity, ``src/babylon/topology/graph.py::BabylonGraph.
query_territory_claims`` (lines 942-959).

Laws pinned (each traces to a specific source range -- see per-test
docstrings for file:line grounding):

  L1 -- Territory-node conservation: a collapse/partition tick never
        creates or destroys Territory nodes. Only Sovereign nodes are
        added (``collapse_transition.py:157-168``, new successor
        Sovereigns) or removed (``collapse_transition.py:276-290``,
        orphan cleanup + the collapsed Sovereign itself once its CLAIMS
        edges are stripped). The set of Territory node IDs is therefore
        invariant across the tick, for ANY legitimacy values, ANY
        winning-faction assignment, and ANY territory count.
  L2 -- Post-collapse CLAIMS partition is exact and exclusive: for every
        Territory the ``winning_faction_by_territory`` map assigns to a
        Faction (``collapse_transition.py:141-149``'s ``by_faction``
        grouping), that Territory ends the tick with EXACTLY ONE CLAIMS
        edge, sourced from the new successor Sovereign for that Faction,
        with ``control_level`` EQUAL (not just bounded) to
        ``BalkanizationDefines.initial_post_collapse_control_level``
        (``collapse_transition.py:169-179``: a plain dict-driven
        assignment, not a computed formula, so equality is exact). A
        Territory the map leaves unassigned (``winning.get(territory_id)
        is None`` at line 143) ends the tick with ZERO CLAIMS edges --
        the documented "Edge case: Unclaimed Territory"
        (``collapse_transition.py:144-148``).
  L3 -- Old-Sovereign CLAIMS stripping: every CLAIMS edge the collapsed
        Sovereign held pre-tick is gone post-tick, unconditionally --
        ``collapse_transition.py:200-201`` removes one CLAIMS edge per
        entry in the pre-collapse ``claims`` list regardless of whether
        that Territory was reassigned to a winning Faction or left
        unclaimed.
  L4 -- Inactivity on empty input: when no Sovereign meets the collapse
        predicate (``legitimacy > 0.0`` and no external trigger,
        ``collapse_transition.py:84-89``), there is no secession-eligible
        entry (``collapse_transition.py:93-95``), and every Sovereign
        already holds at least one CLAIMS edge (so Phase-3 orphan cleanup
        at lines 276-290 has nothing to prune), the tick is a pure no-op
        on graph state: the Sovereign-node set, the Territory-node set,
        and every Sovereign's CLAIMS list are byte-identical before and
        after ``step()``.

Caveat (NOT a law): L1 does NOT imply Sovereign-node conservation -- the
collapsed Sovereign is deleted once orphaned (Phase 3) and zero or more
successor Sovereigns are created (one per distinct winning Faction), so
the Sovereign-node COUNT can rise, fall, or stay flat across a collapse
tick. Only the Territory substrate is conserved (consistent with the
Constitution's "the spatial substrate is immutable" clause).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.collapse_transition import CollapseTransitionSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_CONTROL = BalkanizationDefines().initial_post_collapse_control_level


def _services() -> ServiceContainer:
    return ServiceContainer.create()


def _system() -> CollapseTransitionSystem:
    return CollapseTransitionSystem()


def _territory_ids(graph: BabylonGraph) -> set[str]:
    return {node.id for node in graph.query_nodes(node_type=NodeType.TERRITORY)}


def _sovereign_ids(graph: BabylonGraph) -> set[str]:
    return {node.id for node in graph.query_nodes(node_type=NodeType.SOVEREIGN)}


# Small alphabet -- Faction assignment or None (unclaimed) per Territory.
_FACTION_OR_NONE = st.sampled_from(["FAC_A", "FAC_B", None])


@given(assignments=st.lists(_FACTION_OR_NONE, min_size=0, max_size=6))
@settings(max_examples=25, deadline=None)
def test_territory_nodes_conserved_across_collapse(assignments: list[str | None]) -> None:
    """L1: Territory node IDs are the same set before and after a
    collapse/partition tick, regardless of Faction assignment."""

    graph = BabylonGraph()
    graph.add_node("SOV_TEST", NodeType.SOVEREIGN, legitimacy=0.0)
    territory_ids = [f"HEX_{i:03d}" for i in range(len(assignments))]
    for territory_id in territory_ids:
        graph.add_node(territory_id, NodeType.TERRITORY)
        graph.add_edge(
            "SOV_TEST",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
        )
    winning = {
        tid: faction
        for tid, faction in zip(territory_ids, assignments, strict=True)
        if faction is not None
    }
    before = _territory_ids(graph)

    context = TickContext(
        tick=5,
        persistent_data={"balkanization.winning_faction_by_territory": winning},
    )
    _system().step(graph, _services(), context)

    assert _territory_ids(graph) == before


@given(assignments=st.lists(_FACTION_OR_NONE, min_size=0, max_size=6))
@settings(max_examples=25, deadline=None)
def test_partition_is_exact_and_exclusive(assignments: list[str | None]) -> None:
    """L2: an assigned Territory ends with exactly one CLAIMS edge at the
    exact post-collapse control level; an unassigned Territory ends with
    zero CLAIMS edges."""

    graph = BabylonGraph()
    graph.add_node("SOV_TEST", NodeType.SOVEREIGN, legitimacy=0.0)
    territory_ids = [f"HEX_{i:03d}" for i in range(len(assignments))]
    for territory_id in territory_ids:
        graph.add_node(territory_id, NodeType.TERRITORY)
        graph.add_edge(
            "SOV_TEST",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
        )
    winning = {
        tid: faction
        for tid, faction in zip(territory_ids, assignments, strict=True)
        if faction is not None
    }

    context = TickContext(
        tick=5,
        persistent_data={"balkanization.winning_faction_by_territory": winning},
    )
    _system().step(graph, _services(), context)

    for territory_id, faction in zip(territory_ids, assignments, strict=True):
        claims = graph.query_territory_claims(territory_id)
        if faction is None:
            assert claims == []
        else:
            assert len(claims) == 1
            source_id, control_level, _legal = claims[0]
            source_node = graph.get_node(source_id)
            assert source_node is not None
            assert source_node.attributes.get("ruling_faction_id") == faction
            assert control_level == _CONTROL


@given(n_territories=st.integers(min_value=0, max_value=6))
@settings(max_examples=25, deadline=None)
def test_collapsed_sovereign_loses_all_claims(n_territories: int) -> None:
    """L3: the collapsed Sovereign's original CLAIMS edges are all gone
    post-tick, whether or not the Territory was reassigned."""

    graph = BabylonGraph()
    graph.add_node("SOV_TEST", NodeType.SOVEREIGN, legitimacy=0.0)
    territory_ids = [f"HEX_{i:03d}" for i in range(n_territories)]
    for territory_id in territory_ids:
        graph.add_node(territory_id, NodeType.TERRITORY)
        graph.add_edge(
            "SOV_TEST",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
        )

    context = TickContext(tick=5, persistent_data={})
    _system().step(graph, _services(), context)

    for territory_id in territory_ids:
        assert graph.get_edge("SOV_TEST", territory_id, "claims") is None


@given(
    n_sovereigns=st.integers(min_value=1, max_value=3),
    n_territories_each=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=25, deadline=None)
def test_healthy_graph_is_untouched(n_sovereigns: int, n_territories_each: int) -> None:
    """L4: no collapse trigger, no secession, every Sovereign already
    claims at least one Territory -> the tick is a pure no-op on graph
    state."""

    graph = BabylonGraph()
    for s in range(n_sovereigns):
        sovereign_id = f"SOV_{s:02d}"
        graph.add_node(sovereign_id, NodeType.SOVEREIGN, legitimacy=1.0)
        for t in range(n_territories_each):
            territory_id = f"HEX_{s:02d}_{t:02d}"
            graph.add_node(territory_id, NodeType.TERRITORY)
            graph.add_edge(
                sovereign_id,
                territory_id,
                "claims",
                control_level=1.0,
                legal_status="de_jure",
            )

    sovereigns_before = _sovereign_ids(graph)
    territories_before = _territory_ids(graph)
    claims_before = {
        sovereign_id: graph.query_sovereign_claims(sovereign_id)
        for sovereign_id in sovereigns_before
    }

    context = TickContext(tick=5, persistent_data={})
    _system().step(graph, _services(), context)

    assert _sovereign_ids(graph) == sovereigns_before
    assert _territory_ids(graph) == territories_before
    for sovereign_id in sovereigns_before:
        assert graph.query_sovereign_claims(sovereign_id) == claims_before[sovereign_id]
