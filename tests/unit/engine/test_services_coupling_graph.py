"""The CouplingGraph's first production wiring (Vol III money scissors, U5).

``CouplingGraph`` and ``build_default_coupling_graph`` had ZERO production
callers: the coupling layer was dormant scaffolding. Per Constitution III.10
a construct must not ship as vocabulary, so it is wired here and consumed by
``ContradictionSystem``. These tests pin the wiring; the consumption contract
is pinned in ``tests/unit/engine/systems/test_contradiction_system.py``.
"""

from __future__ import annotations

import pytest

from babylon.domain.dialectics.core.coupling import CouplingGraph
from babylon.domain.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
)
from babylon.engine.services import ServiceContainer

pytestmark = pytest.mark.unit


def _triple(coupling: object) -> tuple[str, str, str]:
    return (coupling.source, coupling.target, coupling.kind)  # type: ignore[attr-defined]


class TestCouplingGraphWiring:
    def test_default_container_carries_a_coupling_graph(self) -> None:
        assert isinstance(ServiceContainer.create().coupling_graph, CouplingGraph)

    def test_default_graph_is_the_production_crisis_producer_map(self) -> None:
        graph = ServiceContainer.create().coupling_graph
        triples = {_triple(c) for c in graph.couplings}
        assert ("surplus_distribution", "debt_spiral", "transforms") in triples
        assert ("credit", "financial", "transforms") in triples

    def test_an_explicit_graph_is_respected(self) -> None:
        registry: OppositionRegistry[object] = OppositionRegistry(bindings=[])
        explicit = CouplingGraph([], registry)
        container = ServiceContainer.create(coupling_graph=explicit)
        assert container.coupling_graph is explicit

    def test_graph_is_built_over_the_injected_registry(self) -> None:
        """A custom registry gets a graph over ITS keys, with every edge whose
        endpoints it does not register dropped — never a KeyError."""
        registry: OppositionRegistry[object] = OppositionRegistry(
            bindings=[
                BoundOpposition(
                    spec=OppositionSpec(key="wage", pole_a="a", pole_b="b"),
                    measure=lambda _inputs: GapReading(gap=0.0, balance=0.0),
                ),
            ]
        )
        container = ServiceContainer.create(opposition_registry=registry)
        assert isinstance(container.coupling_graph, CouplingGraph)
        assert container.coupling_graph.couplings == ()

    def test_protocol_declares_the_attribute(self) -> None:
        from babylon.kernel.services import ServicesProtocol

        assert "coupling_graph" in ServicesProtocol.__annotations__
