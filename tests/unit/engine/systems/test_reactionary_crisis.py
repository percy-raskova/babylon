"""Spec-071 SC-001 / SC-007: induced-crisis engine integration.

Runs the FULL default engine pipeline over an in-memory graph with a labor
aristocrat under sustained crisis (re-injected agitation) plus a fascist
faction present, and asserts the reactionary arc fires end-to-end:
FASCIST_DRIFT accumulates -> fascist_alignment saturates -> the node is
captured (FASCIST_RECRUITMENT + aligned_faction_id). Also asserts determinism
(SC-007): the same scenario twice yields the same event stream.
"""

from __future__ import annotations

import pytest

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.models import SocialClass, WorldState
from babylon.models.enums import EventType, SocialRole
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_CRISIS_AGITATION = 2.0  # pull = 2.0 * (0.8 / 0.1) = 16 >> threshold 1.0
_TICKS = 25  # 0.05/tick drift needs 20 ticks to saturate; give headroom


def _build_engine() -> SimulationEngine:
    return SimulationEngine(systems=[type(s)() for s in _DEFAULT_SYSTEMS])


def _seed_graph() -> tuple[BabylonGraph, str]:
    la = SocialClass(
        id="C001",
        name="labor aristocrat",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=1_000_000.0,  # survive the run (no income circuit here)
        county_fips="26163",
    )
    graph = WorldState(tick=0, entities={"C001": la}).to_graph()
    # Add a fascist faction (spec-070 model) as the capture target.
    graph.add_node(
        "FAC_SETTLER",
        "balkanization_faction",
        is_settler_formation=True,
        colonial_stance="uphold",
        ideology="settler-restorationism",
    )
    return graph, "C001"


def _run_crisis(seed_events: bool = False) -> tuple[list, str | None, float]:
    engine = _build_engine()
    services = ServiceContainer.create()
    graph, la_id = _seed_graph()
    for tick in range(1, _TICKS + 1):
        # Sustain the crisis: re-inject agitation each tick (a decaying bribe).
        node = graph.get_node(la_id)
        ideology = dict(node.attributes.get("ideology", {}))
        ideology["agitation"] = _CRISIS_AGITATION
        graph.update_node(la_id, ideology=ideology)
        engine.run_tick(graph, services, TickContext(tick=tick))

    history = services.event_bus.get_history()
    node = graph.get_node(la_id)
    return (
        history,
        node.attributes.get("aligned_faction_id"),
        float(node.attributes.get("fascist_alignment", 0.0)),
    )


def _count(history: list, event_type: EventType) -> int:
    return sum(1 for e in history if str(e.type) == event_type.value)


class TestInducedCrisisArc:
    def test_drift_then_recruitment_fires(self) -> None:
        history, aligned_faction, alignment = _run_crisis()
        assert _count(history, EventType.FASCIST_DRIFT) > 0, "sustained crisis must drift the LA"
        assert alignment == pytest.approx(1.0), "alignment must saturate over the run"
        assert aligned_faction == "FAC_SETTLER", "saturated node must be captured"
        assert _count(history, EventType.FASCIST_RECRUITMENT) == 1

    def test_determinism_same_event_stream(self) -> None:
        counts_a = self._signature(_run_crisis()[0])
        counts_b = self._signature(_run_crisis()[0])
        assert counts_a == counts_b

    @staticmethod
    def _signature(history: list) -> dict[str, int]:
        return {
            et.value: _count(history, et)
            for et in (EventType.FASCIST_DRIFT, EventType.FASCIST_RECRUITMENT)
        }
