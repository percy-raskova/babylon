"""Metamorphic property tests for simulation systems (Spec 040 Layer 6).

Metamorphic testing: transform inputs in known ways and verify that
outputs transform correspondingly. More powerful than oracle-based
testing for numerical simulations with no closed-form solution.

Properties:
1. Zero-labor homogeneity: zeroing every producer's population zeroes
   ProductionSystem's output (the formula's degree-1 homogeneity law,
   ``f(0) == 0``). Wealth-scaling does NOT scale output — the formula
   never reads an entity's own wealth as an input — so that weaker claim
   is not asserted.
2. Relabeling invariance: renaming entity IDs doesn't change aggregate
   wealth.
3. Production monotonicity: repeated ProductionSystem steps never
   decrease total wealth. ProductionSystem is NOT idempotent by design
   (Phase 1 value-creation adds production on every step it runs), so
   this pins the weaker law that actually holds instead of a false one.
4. Per-step wealth floor: no single entity's own wealth decreases from
   one ProductionSystem step — the system only ever adds to an entity's
   wealth attribute, never subtracts.

``worldstate_strategy`` never wires a TENANCY edge from an entity to a
territory (its relationships are strictly entity-to-entity — see
``tests/property/strategies/worldstate.py``), so ProductionSystem is a
silent no-op on a raw generated graph regardless of any transform under
test. Every check below that exercises ProductionSystem routes through
``_wire_to_productive_territory`` to build a real production scenario
the assertions can actually fail against.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hypothesis import given, settings

from tests.property.strategies.worldstate import worldstate_strategy

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.world_state import WorldState


def _wire_to_productive_territory(state: WorldState) -> tuple[WorldState, GraphProtocol]:
    """Force every entity into an active direct producer and wire TENANCY.

    ``ProductionSystem`` only produces for PERIPHERY_PROLETARIAT/
    LABOR_ARISTOCRACY roles reachable via a TENANCY edge to a territory
    with biocapacity (``babylon.engine.systems.production.ProductionSystem
    .step``). Since ``worldstate_strategy`` never generates such an edge,
    this helper builds one: every entity becomes an active
    PERIPHERY_PROLETARIAT tenant of the state's first territory, whose
    biocapacity is set to full so ``bio_ratio == 1.0`` deterministically.

    Args:
        state: A WorldState with at least one entity and one territory.

    Returns:
        Tuple of the role-adjusted WorldState and its TENANCY-wired graph.
    """
    from babylon.models.enums import EdgeType, SocialRole

    producer_entities = {
        eid: entity.model_copy(update={"role": SocialRole.PERIPHERY_PROLETARIAT, "active": True})
        for eid, entity in state.entities.items()
    }
    connected = state.model_copy(update={"entities": producer_entities})
    territory_id = next(iter(connected.territories))

    graph = connected.to_graph()
    graph.update_node(territory_id, biocapacity=100.0, max_biocapacity=100.0)
    for entity_id in connected.entities:
        graph.add_edge(entity_id, territory_id, edge_type=EdgeType.TENANCY)

    return connected, graph


class TestLaborHomogeneity:
    """Zero labor input yields zero production output.

    ``ProductionSystem``'s formula (``effective_labor_power * population
    * bio_ratio``) is linear in ``population`` — the degree-1
    homogeneity law's zero case, ``f(0) == 0``, holds exactly.
    """

    @given(state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(max_examples=20, deadline=5000)
    def test_zero_population_produces_zero_output(self, state: object) -> None:
        """Zeroing every producer's population leaves wealth unchanged."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.production import ProductionSystem
        from babylon.models.world_state import WorldState

        assert isinstance(state, WorldState)

        zeroed = state.model_copy(
            update={
                "entities": {
                    eid: entity.model_copy(update={"population": 0})
                    for eid, entity in state.entities.items()
                }
            }
        )
        connected, graph = _wire_to_productive_territory(zeroed)

        system = ProductionSystem()
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 0})
        post = WorldState.from_graph(graph, tick=1)

        for entity_id, pre_entity in connected.entities.items():
            post_wealth = post.entities[entity_id].wealth
            assert post_wealth == pre_entity.wealth, (
                f"Entity {entity_id} gained wealth from zero population: "
                f"{pre_entity.wealth} -> {post_wealth}"
            )


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


class TestProductionMonotonicity:
    """Repeated production never decreases total wealth.

    ProductionSystem is Phase 1's value-creation step — it is NOT
    idempotent by design, since it adds production on every step it
    runs. A second application on the post-state is therefore expected
    to differ from the first, not reproduce it. What DOES hold:
    ``produced_value`` (``effective_labor_power * population *
    bio_ratio``) is always >= 0, because all three factors carry a
    ``ge=0`` field constraint, so repeated stepping is monotonically
    non-decreasing in total wealth.
    """

    @given(state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(max_examples=15, deadline=10000)
    def test_double_step_never_decreases_total_wealth(self, state: object) -> None:
        """Total wealth after a second ProductionSystem step is >= after the first."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.production import ProductionSystem
        from babylon.models.world_state import WorldState

        assert isinstance(state, WorldState)

        connected, graph1 = _wire_to_productive_territory(state)
        pre_total = sum(e.wealth for e in connected.entities.values())

        system = ProductionSystem()
        services = ServiceContainer.create()

        system.step(graph1, services, {"tick": 0})
        post1 = WorldState.from_graph(graph1, tick=1)
        total1 = sum(e.wealth for e in post1.entities.values())
        assert total1 >= pre_total, "First production step decreased total wealth"

        graph2 = post1.to_graph()
        system.step(graph2, services, {"tick": 1})
        post2 = WorldState.from_graph(graph2, tick=2)
        total2 = sum(e.wealth for e in post2.entities.values())
        assert total2 >= total1, "Second production step decreased total wealth"


class TestConservationUnderComposition:
    """No entity's own wealth decreases from a single ProductionSystem step.

    Direct producers gain their own ``produced_value``; every other
    branch (inactive workers, non-producer roles, Labor Aristocracy
    routed to an employer) leaves an entity's own ``wealth`` attribute
    untouched. Nothing in ``ProductionSystem.step`` subtracts from an
    entity's wealth, so per-entity wealth is a floor. This is distinct
    from "total wealth is conserved": production adds new value from
    hydrated capital stocks each tick rather than preserving the
    pre-tick total (see ``TestProductionMonotonicity``).
    """

    @given(state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(max_examples=20, deadline=5000)
    def test_no_entity_wealth_decreases_after_production(self, state: object) -> None:
        """Every entity's wealth after ProductionSystem is >= its wealth before."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.production import ProductionSystem
        from babylon.models.world_state import WorldState

        assert isinstance(state, WorldState)

        connected, graph = _wire_to_productive_territory(state)

        system = ProductionSystem()
        services = ServiceContainer.create()
        system.step(graph, services, {"tick": 0})
        post = WorldState.from_graph(graph, tick=1)

        for entity_id, pre_entity in connected.entities.items():
            post_wealth = post.entities[entity_id].wealth
            assert post_wealth >= pre_entity.wealth, (
                f"Entity {entity_id} lost wealth from ProductionSystem: "
                f"{pre_entity.wealth} -> {post_wealth}"
            )
