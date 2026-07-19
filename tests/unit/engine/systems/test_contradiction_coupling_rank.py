"""The CouplingGraph's earn-its-keep duty (owner-approved, Vol III U5).

Constitution III.10 forbids shipping a construct as vocabulary, so the
coupling graph gets a job: it constrains principal-contradiction ranking.
A ``transforms`` edge means "the source's output becomes the target's
input" — so a target cannot lead the whole formation while the source that
supplies it reads ABSENT. Crisis has a direction of travel, and the
coupling graph is what knows it.

This is the ONE place the Vol III design alters existing semantics rather
than filling absence, so the contract is pinned in BOTH directions: the
target is demoted when its source is absent, and it ranks completely
normally when the source is present.
"""

from __future__ import annotations

import pytest

from babylon.domain.dialectics.core.coupling import Coupling, CouplingGraph
from babylon.domain.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
)
from babylon.domain.dialectics.instances.catalog import GraphInputs
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import (
    OPPOSITION_STATES_ATTR,
    ContradictionSystem,
)
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _binding(key: str, gap: float, balance: float) -> BoundOpposition[GraphInputs]:
    """A binding whose measure is a constant — the ranking is the subject."""
    reading = GapReading(gap=gap, balance=balance)
    return BoundOpposition(
        spec=OppositionSpec(key=key, pole_a=f"{key}-a", pole_b=f"{key}-b"),
        measure=lambda _inputs, _reading=reading: _reading,  # type: ignore[misc]
    )


def _services(
    *,
    source_gap: float,
    source_balance: float,
) -> ServiceContainer:
    """A three-opposition world: source --transforms--> target, plus a rival.

    ``target`` carries the top score (gap 0.9), ``rival`` the runner-up
    (gap 0.6), ``source`` the reading under test.
    """
    registry: OppositionRegistry[GraphInputs] = OppositionRegistry(
        bindings=[
            _binding("source", source_gap, source_balance),
            _binding("target", 0.9, 0.5),
            _binding("rival", 0.6, 0.5),
        ],
        rate_weight=10.0,
    )
    coupling_graph = CouplingGraph(
        [Coupling(source="source", target="target", kind="transforms")],
        registry,
    )
    return ServiceContainer.create(
        opposition_registry=registry,
        coupling_graph=coupling_graph,
    )


def _principal(graph: BabylonGraph) -> str:
    states = graph.get_graph_attr(OPPOSITION_STATES_ATTR, {})
    return next(key for key, dump in states.items() if dump["is_principal"])


class TestTransformsSourceAbsent:
    """(0.0, 0.0) is the catalog's canonical ABSENT reading."""

    def test_target_is_demoted_and_the_runner_up_leads(self) -> None:
        graph = BabylonGraph()
        services = _services(source_gap=0.0, source_balance=0.0)
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        assert _principal(graph) == "rival"

    def test_the_demoted_target_carries_is_principal_false(self) -> None:
        graph = BabylonGraph()
        services = _services(source_gap=0.0, source_balance=0.0)
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        states = graph.get_graph_attr(OPPOSITION_STATES_ATTR, {})
        assert states["target"]["is_principal"] is False

    def test_the_demotion_is_visible_to_the_frames(self) -> None:
        """Frames are derived AFTER the correction, so the narrative layer
        never announces a principal the engine has demoted."""
        graph = BabylonGraph()
        services = _services(source_gap=0.0, source_balance=0.0)
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        frames = graph.get_graph_attr("contradiction_frames", {})
        assert frames["global"]["principal"]["id"] == "rival"

    def test_the_targets_gap_is_untouched_only_its_rank_changes(self) -> None:
        graph = BabylonGraph()
        services = _services(source_gap=0.0, source_balance=0.0)
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        states = graph.get_graph_attr(OPPOSITION_STATES_ATTR, {})
        assert states["target"]["gap"] == pytest.approx(0.9)


class TestTransformsSourcePresent:
    """The other direction — the rule must not fire when it should not."""

    def test_target_ranks_principal_normally(self) -> None:
        graph = BabylonGraph()
        services = _services(source_gap=0.2, source_balance=0.1)
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        assert _principal(graph) == "target"

    def test_a_zero_gap_with_a_leading_pole_is_present_not_absent(self) -> None:
        """gap 0 with balance −1 is what every Vol III ratio measure returns
        for a claim of zero: a real reading of no claim, NOT missing data.
        Only the (0, 0) pair means absent."""
        graph = BabylonGraph()
        services = _services(source_gap=0.0, source_balance=-1.0)
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        assert _principal(graph) == "target"


class TestRuleIsInertWithoutTheGraph:
    def test_no_coupling_graph_leaves_ranking_untouched(self) -> None:
        registry: OppositionRegistry[GraphInputs] = OppositionRegistry(
            bindings=[
                _binding("source", 0.0, 0.0),
                _binding("target", 0.9, 0.5),
                _binding("rival", 0.6, 0.5),
            ],
            rate_weight=10.0,
        )
        graph = BabylonGraph()
        services = ServiceContainer.create(
            opposition_registry=registry,
            coupling_graph=None,
        )
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        assert _principal(graph) == "target"

    def test_non_transforms_edges_never_demote(self) -> None:
        """``feeds`` and ``constrains`` carry no such prohibition: only
        ``transforms`` means the source's output IS the target's input."""
        registry: OppositionRegistry[GraphInputs] = OppositionRegistry(
            bindings=[
                _binding("source", 0.0, 0.0),
                _binding("target", 0.9, 0.5),
                _binding("rival", 0.6, 0.5),
            ],
            rate_weight=10.0,
        )
        coupling_graph = CouplingGraph(
            [Coupling(source="source", target="target", kind="feeds")],
            registry,
        )
        graph = BabylonGraph()
        services = ServiceContainer.create(
            opposition_registry=registry, coupling_graph=coupling_graph
        )
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        assert _principal(graph) == "target"


class TestEveryCandidateBlocked:
    def test_the_original_principal_is_kept_rather_than_leaving_none(self) -> None:
        """A tick must never end with no principal contradiction; when every
        eligible candidate is blocked the original stands."""
        registry: OppositionRegistry[GraphInputs] = OppositionRegistry(
            bindings=[
                _binding("source", 0.0, 0.0),
                _binding("target", 0.9, 0.5),
            ],
            rate_weight=10.0,
        )
        coupling_graph = CouplingGraph(
            [Coupling(source="source", target="target", kind="transforms")],
            registry,
        )
        graph = BabylonGraph()
        services = ServiceContainer.create(
            opposition_registry=registry, coupling_graph=coupling_graph
        )
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        # source is itself absent (gap 0) so it can never outscore target;
        # target is blocked; the fallback keeps target rather than returning
        # a principal-less tick.
        assert _principal(graph) == "target"
