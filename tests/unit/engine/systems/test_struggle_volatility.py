"""Spec-071: LUMPENPROLETARIAT volatility -> SPONTANEOUS_RIOT in StruggleSystem.

The declassed stratum's undirected disorder is gated by
``volatility × (1 − organizational_discipline)`` — distinct from the
organized, solidarity-building UPRISING (it destroys wealth but builds NO
solidarity infrastructure). The riot is a deterministic gate (III.7);
the spark roll in the main loop uses the tick-seeded stream, so no global
RNG seeding is needed anywhere here.
"""

from __future__ import annotations

import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.struggle import StruggleSystem
from babylon.models.enums import EdgeType, EventType

pytestmark = pytest.mark.unit


@pytest.fixture
def services() -> ServiceContainer:
    return ServiceContainer.create()


def _events(services: ServiceContainer, et: EventType) -> list:
    return [e for e in services.event_bus.get_history() if str(e.type) == et.value]


def _add_lumpen(g: BabylonGraph, *, volatility: float, organization: float) -> None:
    g.add_node(
        "C001",
        "social_class",
        role="lumpenproletariat",
        active=True,
        wealth=10.0,
        volatility=volatility,
        organization=organization,
        ideology={"class_consciousness": 0.0, "national_identity": 0.5, "agitation": 0.0},
    )


class TestSpontaneousRiot:
    def test_high_volatility_low_discipline_riots(self, services: ServiceContainer) -> None:
        g = BabylonGraph()
        _add_lumpen(g, volatility=0.8, organization=0.0)  # risk = 0.8 > threshold 0.5
        StruggleSystem().step(g, services, {"tick": 3})
        riots = _events(services, EventType.SPONTANEOUS_RIOT)
        assert len(riots) == 1
        # Riot destroys wealth ...
        assert g.get_node("C001").attributes["wealth"] < 10.0
        # ... but builds NO solidarity infrastructure.
        assert not any(
            e.attributes.get("solidarity_strength", 0.0) > 0.0
            for e in g.query_edges(edge_type=EdgeType.SOLIDARITY)
        )

    def test_high_discipline_suppresses_riot(self, services: ServiceContainer) -> None:
        g = BabylonGraph()
        _add_lumpen(g, volatility=0.8, organization=1.0)  # risk = 0.0 -> never fires
        StruggleSystem().step(g, services, {"tick": 3})
        assert _events(services, EventType.SPONTANEOUS_RIOT) == []

    def test_zero_volatility_no_riot(self, services: ServiceContainer) -> None:
        g = BabylonGraph()
        _add_lumpen(g, volatility=0.0, organization=0.0)
        StruggleSystem().step(g, services, {"tick": 3})
        assert _events(services, EventType.SPONTANEOUS_RIOT) == []

    def test_determinism_same_tick_same_outcome(self, services: ServiceContainer) -> None:
        outcomes = []
        for _ in range(2):
            svc = ServiceContainer.create()
            g = BabylonGraph()
            _add_lumpen(g, volatility=0.8, organization=0.0)
            StruggleSystem().step(g, svc, {"tick": 3})
            outcomes.append(len(_events(svc, EventType.SPONTANEOUS_RIOT)))
        assert outcomes[0] == outcomes[1]
