"""Property-based tests for the No-DB-I/O-during-tick causal invariant
(INV-015 / spec-056 US3).

See ``specs/056-causal-invariants/contracts/no_db_io_during_tick.md`` for
the full predicate specification. Encodes Constitution II.6 verbatim
("No DB I/O during tick"), II.10 World Runtime, II.11 Subsystem Table
Ownership, and ADR037 Postgres Runtime — the engine is a pure
transformation; intra-tick I/O is non-determinism by another name.

Three predicates:

  AS1 — Random WorldState run_tick under no_db_io_during_tick patch succeeds (T021)
  AS2 — Deliberate DB call from a System raises DBIONotPermittedError (T022)
  AS3 — Hydration before patch + persistence after patch are uninterrupted (T023)
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph
from tests.property.harness.causal_harness import (
    DBIONotPermittedError,
    no_db_io_during_tick,
)
from tests.property.strategies.worldstate import worldstate_strategy


def _build_default_engine() -> SimulationEngine:
    """Engine with the canonical _DEFAULT_SYSTEMS (causality order)."""
    return SimulationEngine(systems=[type(s)() for s in _DEFAULT_SYSTEMS])


@pytest.mark.unit
class TestNoDbIoDuringTick:
    """INV-015: no DB-bearing service is touched during run_tick."""

    @given(state=worldstate_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_clean_tick_under_no_db_io_patch(
        self,
        state: WorldState,
    ) -> None:
        """AS1: a random WorldState's run_tick completes without raising
        DBIONotPermittedError when wrapped in no_db_io_during_tick."""
        services = ServiceContainer.create()
        ctx = TickContext(tick=state.tick)
        engine = _build_default_engine()

        with no_db_io_during_tick(services):
            engine.run_tick(state.to_graph(), services, ctx)

    def test_deliberate_db_call_is_caught(self) -> None:
        """AS2: a System whose step() touches services.database.execute
        raises DBIONotPermittedError under the patched scope. Negative
        test, no Hypothesis."""
        from typing import Any

        import networkx as nx

        services = ServiceContainer.create()
        ctx = TickContext(tick=0)

        class BadSystem:
            """A System that violates II.6 by touching the DB mid-tick."""

            @property
            def name(self) -> str:
                return "bad_system"

            def step(
                self,
                graph: nx.DiGraph,
                services_arg: Any,
                context: Any,
            ) -> None:
                # The forbidden call:
                services_arg.database.execute("SELECT 1")

        engine = SimulationEngine(systems=[BadSystem()])
        graph = BabylonGraph()

        with no_db_io_during_tick(services), pytest.raises(DBIONotPermittedError) as exc_info:
            engine.run_tick(graph, services, ctx)

        # Confirm the exception names the database surface and the execute attribute
        assert exc_info.value.surface == "database", (
            f"Expected surface='database', got {exc_info.value.surface!r}"
        )
        assert exc_info.value.attribute == "execute", (
            f"Expected attribute='execute', got {exc_info.value.attribute!r}"
        )

    def test_hydration_and_persistence_outside_patch_succeed(self) -> None:
        """AS3: the patched scope is exactly the run_tick call —
        hydration BEFORE entering the scope and persistence AFTER
        exiting work uninterrupted. Negative test, no Hypothesis."""

        from babylon.persistence import RuntimeDatabase

        services = ServiceContainer.create()
        ctx = TickContext(tick=0)
        engine = _build_default_engine()

        # PRE-tick hydration: real DB access is permitted (we're outside
        # the no_db_io_during_tick scope)
        runtime_db = RuntimeDatabase(in_memory=True)
        # Persist a baseline tick to demonstrate the DB is reachable
        runtime_db.persist_tick(tick=-1, graph=BabylonGraph())

        # Run the tick under the no-DB-I/O scope (clean — no intra-tick I/O)
        state = WorldState(tick=0)
        with no_db_io_during_tick(services):
            engine.run_tick(state.to_graph(), services, ctx)

        # POST-tick persistence: real DB access is again permitted
        runtime_db.persist_tick(tick=0, graph=state.to_graph())

        # Verify the post-tick persistence actually wrote something
        recovered = runtime_db.hydrate_graph(tick=0)
        assert recovered is not None
        runtime_db.close()
