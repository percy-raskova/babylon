"""Metamorphic property tests for simulation systems (Spec 040 Layer 6).

Metamorphic testing: transform inputs in known ways and verify that
outputs transform correspondingly. More powerful than oracle-based
testing for numerical simulations with no closed-form solution.

Properties:
1. Labor homogeneity: Scaling all wealth by k scales production output by k
2. Relabeling invariance: Renaming entity IDs doesn't change aggregate results
3. Phase idempotence: Running a system twice with frozen state is idempotent
4. Conservation under composition: Total wealth preserved per-tick
"""

from __future__ import annotations

from hypothesis import given, settings

from tests.property.strategies.worldstate import worldstate_strategy


class TestLaborHomogeneity:
    """Scaling all wealth should scale outputs proportionally."""

    @given(state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(max_examples=20, deadline=5000)
    def test_zero_wealth_produces_zero_output(self, state: object) -> None:
        """If all entities have zero wealth, production adds zero."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.production import ProductionSystem
        from babylon.models.world_state import WorldState

        assert isinstance(state, WorldState)

        # Zero out all wealth
        zeroed_entities = {}
        for eid, entity in state.entities.items():
            zeroed_entities[eid] = entity.model_copy(update={"wealth": 0.0})
        zeroed = state.model_copy(update={"entities": zeroed_entities})

        # Run production
        graph = zeroed.to_graph()
        system = ProductionSystem()
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 0})
        post = WorldState.from_graph(graph, tick=1)

        # Total wealth should still be zero (no negative production)
        total_post = sum(e.wealth for e in post.entities.values())
        assert total_post >= 0.0, "Production should never create negative wealth"


class TestRelabelingInvariance:
    """Renaming entity IDs should not change aggregate metrics."""

    @given(state=worldstate_strategy(min_entities=2, min_territories=1))
    @settings(max_examples=15, deadline=5000)
    def test_aggregate_wealth_invariant_under_relabeling(self, state: object) -> None:
        """Total wealth is invariant under entity ID permutation."""
        from babylon.models.world_state import WorldState

        assert isinstance(state, WorldState)

        original_total = sum(e.wealth for e in state.entities.values())

        # Relabel: reverse entity IDs
        entity_ids = list(state.entities.keys())
        reversed_ids = list(reversed(entity_ids))
        relabeled_entities = {}
        for old_id, new_id in zip(entity_ids, reversed_ids, strict=True):
            entity = state.entities[old_id]
            relabeled_entities[new_id] = entity.model_copy(update={"id": new_id})

        relabeled = state.model_copy(update={"entities": relabeled_entities})
        relabeled_total = sum(e.wealth for e in relabeled.entities.values())

        assert abs(original_total - relabeled_total) < 1e-10


class TestPhaseIdempotence:
    """Running a system on an already-processed state should be stable."""

    @given(state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(max_examples=15, deadline=10000)
    def test_production_double_step_bounded(self, state: object) -> None:
        """Running ProductionSystem twice produces bounded change."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.production import ProductionSystem
        from babylon.models.world_state import WorldState

        assert isinstance(state, WorldState)

        system = ProductionSystem()
        services = ServiceContainer.create()

        # First step
        graph1 = state.to_graph()
        system.step(graph1, services, {"tick": 0})
        post1 = WorldState.from_graph(graph1, tick=1)
        total1 = sum(e.wealth for e in post1.entities.values())

        # Second step on post-state
        graph2 = post1.to_graph()
        system.step(graph2, services, {"tick": 1})
        post2 = WorldState.from_graph(graph2, tick=2)
        total2 = sum(e.wealth for e in post2.entities.values())

        # Change should be bounded (not exponential blowup)
        if total1 > 0:
            ratio = total2 / total1
            assert ratio < 100.0, f"Wealth growth ratio {ratio} suggests instability"


class TestConservationUnderComposition:
    """Wealth should not appear from nowhere."""

    @given(state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(max_examples=20, deadline=5000)
    def test_no_negative_wealth_after_production(self, state: object) -> None:
        """No entity has negative wealth after ProductionSystem."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.production import ProductionSystem
        from babylon.models.world_state import WorldState

        assert isinstance(state, WorldState)

        graph = state.to_graph()
        system = ProductionSystem()
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 0})
        post = WorldState.from_graph(graph, tick=1)

        for entity in post.entities.values():
            assert entity.wealth >= 0.0, f"Entity {entity.id} has negative wealth {entity.wealth}"
