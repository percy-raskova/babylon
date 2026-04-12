"""Invariant harness test.

Spec 040 Discipline 1: Automated invariant checking.

The harness discovers systems that declare invariants and runs Hypothesis
to verify those invariants hold across random state transitions.
"""

from hypothesis import given, settings

from tests.property.strategies.worldstate import worldstate_strategy


class TestInvariantHarness:
    """Run invariants against system steps on random state."""

    @given(state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(max_examples=20, deadline=5000)
    def test_production_system_preserves_invariants(self, state: object) -> None:
        """ProductionSystem preserves its declared invariants on random state."""
        from babylon.engine.invariants import Invariant
        from babylon.engine.systems.production import ProductionSystem
        from babylon.models.world_state import WorldState

        system = ProductionSystem()

        # System must declare invariants (Spec 040)
        invariants: list[Invariant] = getattr(system, "invariants", [])
        assert len(invariants) > 0, "ProductionSystem must declare invariants"

        # Snapshot pre-state
        assert isinstance(state, WorldState)
        pre = state

        # Run system step via graph round-trip
        graph = pre.to_graph()
        # Build minimal services using factory method
        from babylon.engine.services import ServiceContainer

        services = ServiceContainer.create()
        context = {"tick": pre.tick}

        system.step(graph, services, context)

        # Reconstruct post-state
        post = WorldState.from_graph(graph, tick=pre.tick + 1)

        # Check all declared invariants
        for invariant in invariants:
            result = invariant.check(pre, post)
            assert result.ok, (
                f"Invariant '{invariant.name}' violated after ProductionSystem.step(): {result.msg}"
            )
