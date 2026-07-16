"""Integration tests for RUPTURE events under Lawverian gap semantics (C1.6).

The rewrite retires the old "tension accumulates to 1.0 -> RUPTURE" mechanism.
A RUPTURE now fires only when the **principal** opposition's gap EXCEEDS the
``rupture_gap_threshold`` **AND is rising** (rate > 0) — Mao's "condition AND
level" (project/06 §9.4), never on a saturating ceiling. Consequences these
tests pin:

- a *static* extreme wealth gap no longer ruptures (no rising edge);
- a *falling* principal gap (e.g. a bribed labor aristocracy catching up) does
  not rupture even while the gap is above threshold;
- an atomized class (no SOLIDARITY) is dominated by the ``atomization``
  opposition (gap 1.0), so the capital_labor contradiction cannot rupture until
  atomization is overcome — a genuine dialectical result;
- a *rising* principal gap above threshold DOES fire RUPTURE.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.factories import (
    create_bourgeoisie,
    create_labor_aristocracy,
    create_proletariat,
)
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation import Simulation
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState
from babylon.models.entity_registry import COMPRADOR_ID, PERIPHERY_WORKER_ID
from babylon.models.enums import EventType
from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.integration, pytest.mark.theory_solidarity]


def _rupture_events(services: ServiceContainer) -> list[object]:
    return [e for e in services.event_bus.get_history() if e.type == EventType.RUPTURE]


class TestRuptureGateFacade:
    """The rupture gate observed end-to-end through the Simulation facade."""

    def test_static_extreme_gap_does_not_rupture(self) -> None:
        """A static extreme wealth gap no longer ruptures (old trigger retired).

        With no SOLIDARITY edge the two classes are fully atomized, so the
        principal contradiction is ``atomization`` (gap 1.0, static). The
        capital_labor gap sits at ~0.98 but never rises, and no RUPTURE fires —
        the class must first overcome atomization.
        """
        worker = create_proletariat(id=PERIPHERY_WORKER_ID, name="Worker", wealth=10.0)
        owner = create_bourgeoisie(id=COMPRADOR_ID, name="Owner", wealth=1000.0)
        edge = Relationship(
            source_id=COMPRADOR_ID,
            target_id=PERIPHERY_WORKER_ID,
            edge_type=EdgeType.EXPLOITATION,
            tension=0.0,
        )
        state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
            relationships=[edge],
        )
        final = Simulation(state, SimulationConfig(), defines=GameDefines()).run(30)

        assert [log for log in final.event_log if "RUPTURE" in log] == []

    def test_falling_principal_gap_does_not_rupture(self) -> None:
        """A high-but-FALLING principal gap (the imperial bribe) does not rupture.

        A labor aristocrat joined by SOLIDARITY to its employer makes
        capital_labor the principal opposition (atomization defused), but the
        bribe lifts the aristocrat's wealth toward the employer so the gap FALLS
        (rate < 0). Above threshold yet not rising -> no rupture.
        """
        la = create_labor_aristocracy(id=PERIPHERY_WORKER_ID, name="Aristocrat", wealth=2.0)
        boss = create_bourgeoisie(id=COMPRADOR_ID, name="Employer", wealth=80.0)
        exploitation = Relationship(
            source_id=COMPRADOR_ID,
            target_id=PERIPHERY_WORKER_ID,
            edge_type=EdgeType.EXPLOITATION,
            tension=0.0,
        )
        solidarity = Relationship(
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.9,
        )
        state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: la, COMPRADOR_ID: boss},
            relationships=[exploitation, solidarity],
        )
        final = Simulation(state, SimulationConfig(), defines=GameDefines()).run(10)

        assert [log for log in final.event_log if "RUPTURE" in log] == []


class TestRuptureGateSystem:
    """The rupture gate driven directly through ContradictionSystem across ticks.

    Uses a raw graph whose nodes carry no ``social_class`` type, so the
    ``atomization`` measure sees an empty solidarity subgraph (gap 0) and
    capital_labor is the principal — isolating the condition-AND-level gate.
    """

    def _graph(self, owner_wealth: float) -> BabylonGraph:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=1.0)
        graph.add_node("owner", wealth=owner_wealth)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        return graph

    def test_rising_principal_gap_above_threshold_ruptures(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._graph(50.0)  # gap ~0.96 (rate 0 on the first tick)

        system.step(graph, services, {"tick": 1})
        assert _rupture_events(services) == []  # high but not yet rising

        graph.nodes["owner"]["wealth"] = 400.0  # gap ~0.995, rising -> rate > 0
        system.step(graph, services, {"tick": 2})

        ruptures = _rupture_events(services)
        assert len(ruptures) == 1
        assert ruptures[0].payload["opposition"] == "capital_labor"
        assert ruptures[0].payload["gap"] > 0.9
        assert ruptures[0].payload["rate"] > 0.0

    def test_falling_gap_after_threshold_does_not_re_rupture(self) -> None:
        """Once the gap starts falling, no further RUPTURE fires (no ceiling latch)."""
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._graph(400.0)  # gap ~0.995

        system.step(graph, services, {"tick": 1})
        graph.nodes["owner"]["wealth"] = 100.0  # gap falls -> rate < 0
        system.step(graph, services, {"tick": 2})
        graph.nodes["owner"]["wealth"] = 60.0  # still falling
        system.step(graph, services, {"tick": 3})

        assert _rupture_events(services) == []


class TestRuptureIsPerPrincipal:
    """RUPTURE is a frame-level event on the principal opposition, not per edge."""

    def test_multi_edge_scenario_reports_principal_opposition(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = BabylonGraph()
        graph.add_node("w1", wealth=1.0)
        graph.add_node("w2", wealth=1.0)
        graph.add_node("owner", wealth=50.0)
        graph.add_edge("w1", "owner", edge_type=EdgeType.EXPLOITATION)
        graph.add_edge("w2", "owner", edge_type=EdgeType.EXPLOITATION)

        system.step(graph, services, {"tick": 1})
        graph.nodes["owner"]["wealth"] = 500.0  # widen both -> mean gap rises
        system.step(graph, services, {"tick": 2})

        ruptures = _rupture_events(services)
        assert len(ruptures) == 1  # one frame-level rupture, not one-per-edge
        assert ruptures[0].payload["opposition"] == "capital_labor"
