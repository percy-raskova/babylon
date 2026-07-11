"""Alarm event emission test (T062 / FR-047 / Clarification Q3).

Subscribes a handler to ``EventBus`` for ``event_type="conservation_alarm"``,
runs the engine through one tick with an evaluator that produces an
ALARM-severity row, and asserts the handler received exactly one ``Event``
with the expected payload.

The engine wire-up wraps the ``ConservationAlarmEvent`` Pydantic model into
a frozen ``Event(type, tick, payload)`` so the bus subscription routes
correctly. This test exists to lock that contract in place.
"""

from __future__ import annotations

import pytest

from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


def test_conservation_alarm_event_published_to_bus():
    """ALARM-severity audit row → exactly one conservation_alarm Event on the bus."""
    from uuid import uuid4

    from babylon.engine.simulation_engine import SimulationEngine
    from babylon.kernel.event_bus import Event, EventBus
    from babylon.persistence.conservation_audit import ConservationAuditor, _InvariantResult

    received: list[Event] = []

    def capture(event: Event) -> None:
        received.append(event)

    bus = EventBus()
    bus.subscribe("conservation_alarm", capture)

    auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)

    def alarming_evaluator(pre, post, ctx):  # noqa: ARG001
        return [
            _InvariantResult(
                scale="county",
                invariant_name="hex_to_county_sum_c",
                computed_value=10.0,
                expected_value=12.5,  # residual = -2.5 → ALARM (>1e-6)
            )
        ]

    auditor.register_invariant("hex_to_county_sum_c", alarming_evaluator)

    # Build a minimal engine with a single hex; we don't need any real Systems.
    engine = SimulationEngine(systems=[], auditor=auditor)
    graph = BabylonGraph()
    graph.add_node(
        "872d34a89ffffff",
        _node_type="hex",
        county_fips="26163",
        c=10.0,
        v=5.0,
        s=3.0,
        k=100.0,
        biocapacity_stock=20.0,
        energy_stock=10.0,
        raw_material_stock=5.0,
    )

    class _Services:
        event_bus = bus

    sid = uuid4()
    engine.run_tick(graph, _Services(), {"tick": 7, "session_id": sid})

    assert len(received) == 1, f"Expected one alarm event, got {len(received)}"
    event = received[0]
    assert event.type == "conservation_alarm"
    assert event.tick == 7
    assert event.payload["invariant_name"] == "hex_to_county_sum_c"
    assert event.payload["scale"] == "county"
    assert event.payload["residual"] == -2.5


def test_no_alarm_event_when_severity_ok():
    """OK-severity rows do NOT publish to the bus."""
    from uuid import uuid4

    from babylon.engine.simulation_engine import SimulationEngine
    from babylon.kernel.event_bus import Event, EventBus
    from babylon.persistence.conservation_audit import ConservationAuditor, _InvariantResult

    received: list[Event] = []

    def capture(event: Event) -> None:
        received.append(event)

    bus = EventBus()
    bus.subscribe("conservation_alarm", capture)

    auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)

    def ok_evaluator(pre, post, ctx):  # noqa: ARG001
        return [
            _InvariantResult(
                scale="county",
                invariant_name="hex_to_county_sum_c",
                computed_value=10.0,
                expected_value=10.0,  # residual = 0 → OK
            )
        ]

    auditor.register_invariant("hex_to_county_sum_c", ok_evaluator)

    engine = SimulationEngine(systems=[], auditor=auditor)
    graph = BabylonGraph()
    graph.add_node("872d34a89ffffff", _node_type="hex")

    class _Services:
        event_bus = bus

    engine.run_tick(graph, _Services(), {"tick": 0, "session_id": uuid4()})

    assert received == []
