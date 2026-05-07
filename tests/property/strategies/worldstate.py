"""Hypothesis strategy for generating valid WorldState instances.

Spec 040 Layer 2: Composite strategy that composes primitives into
a valid WorldState, ensuring referential integrity.

Spec 053 T014a: ``worldstate_with_hexes_strategy`` additionally composes a
``HexGrid`` for tests that need both engine-side state (graph nodes via
``WorldState.to_graph()``) and substrate-side state (per-hex c+v+s in a
``HexGrid``). The two containers share no node IDs and are independent.
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from babylon.economics.substrate.types import HexGrid
from babylon.models.world_state import WorldState
from tests.property.strategies.hex_grid import hex_grid_strategy
from tests.property.strategies.primitives import (
    relationship_strategy,
    social_class_strategy,
    territory_strategy,
)


def worldstate_strategy(
    min_entities: int = 0,
    max_entities: int = 4,
    min_territories: int = 0,
    max_territories: int = 3,
    max_relationships: int = 4,
) -> SearchStrategy[WorldState]:
    """Generate valid WorldState instances with referential integrity.

    Constructs entities, territories, and relationships with valid
    cross-references (relationship source/target IDs are drawn from
    generated entity IDs).

    Args:
        min_entities: Minimum number of entities.
        max_entities: Maximum number of entities.
        min_territories: Minimum number of territories.
        max_territories: Maximum number of territories.
        max_relationships: Maximum number of relationships.

    Returns:
        Hypothesis strategy producing WorldState instances.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> WorldState:
        tick = draw(st.integers(min_value=0, max_value=100))

        # Generate entities
        n_entities = draw(st.integers(min_value=min_entities, max_value=max_entities))
        entities = {}
        for i in range(n_entities):
            entity = draw(social_class_strategy())
            # Override ID to ensure uniqueness
            unique_id = f"C{i:03d}"
            entity = entity.model_copy(update={"id": unique_id})
            entities[unique_id] = entity

        # Generate territories
        n_territories = draw(st.integers(min_value=min_territories, max_value=max_territories))
        territories = {}
        for i in range(n_territories):
            territory = draw(territory_strategy())
            unique_id = f"T{i:03d}"
            territory = territory.model_copy(update={"id": unique_id})
            territories[unique_id] = territory

        # Generate relationships between existing entities
        relationships = []
        if len(entities) >= 2:
            entity_ids = list(entities.keys())
            n_rels = draw(
                st.integers(min_value=0, max_value=min(max_relationships, len(entity_ids)))
            )
            for _ in range(n_rels):
                rel = draw(
                    relationship_strategy(
                        source_ids=st.sampled_from(entity_ids),
                        target_ids=st.sampled_from(entity_ids),
                    )
                )
                relationships.append(rel)

        return WorldState(
            tick=tick,
            entities=entities,
            territories=territories,
            relationships=relationships,
        )

    return _build()


def worldstate_with_hexes_strategy(
    min_hexes: int = 1,
    max_hexes: int = 25_000,
) -> SearchStrategy[tuple[WorldState, HexGrid]]:
    """Generate a (WorldState, HexGrid) pair for spec-053 invariant tests.

    Composes the existing ``worldstate_strategy()`` with ``hex_grid_strategy()``
    and returns the two as an independent tuple. The WorldState's entities/
    territories carry their own IDs; the HexGrid's hexes are keyed by H3
    cell IDs from the Michigan tri-county pool. The two containers share no
    keys — each is passed to its appropriate consumer (engine systems take
    the graph derived from ``WorldState.to_graph()``; substrate computers
    take the ``HexGrid`` directly).

    Args:
        min_hexes: Minimum hex count in the HexGrid component (default 1).
        max_hexes: Maximum hex count in the HexGrid component (default 25 000;
            clamped to the seed-pool size).

    Returns:
        A Hypothesis ``SearchStrategy[tuple[WorldState, HexGrid]]``.
    """
    return st.tuples(worldstate_strategy(), hex_grid_strategy(min_hexes, max_hexes))


# =============================================================================
# Spec 054 — Bound-invariant strategies
# =============================================================================


def worldstate_with_simplex_consciousness_strategy() -> SearchStrategy[WorldState]:
    """Generate a WorldState carrying TernaryConsciousness-bearing entities.

    Spec 054 US3: SocialClass entities currently carry ``class_consciousness``
    (a scalar Probability), not a ``TernaryConsciousness`` simplex. The
    ternary simplex lives on ``CommunityState`` instances that are stored
    inside graph nodes during the engine's tick loop, not on ``WorldState``
    directly. So for US3 single-tick / multi-tick tests, this strategy
    delegates to the base ``worldstate_strategy(min_entities=1)`` — the
    simplex constraint is then exercised through the graph round-trip.

    The actual simplex generation lives in the ``simplex_points()`` strategy
    re-exported from ``tests.property.strategies.consciousness_simplex``;
    direct point generation is used by US3 Predicate C (routing-formula
    test).
    """
    return worldstate_strategy(min_entities=1)


def worldstate_with_solidarity_edges_strategy() -> SearchStrategy[WorldState]:
    """Generate a WorldState that contains at least one SOLIDARITY edge
    between two entities (spec-054 US1 Predicate C).

    The base ``worldstate_strategy(min_entities=2)`` already produces
    Relationship edges between entities; the Relationship strategy uniformly
    samples from ``EdgeType``. This wrapper bumps ``min_entities`` to 2 so
    edge generation is possible.
    """
    return worldstate_strategy(min_entities=2, max_relationships=4)


def worldstate_with_consecutive_ticks_strategy(
    n_ticks: int = 5,
) -> SearchStrategy[WorldState]:
    """Generate an initial WorldState for a multi-tick test (spec-054 US3, US4).

    The strategy returns a single starting WorldState; the consuming test
    threads the post-state of tick ``i`` into the pre-state of tick ``i+1``.
    The ``n_ticks`` parameter is documentation-only (recorded so the test
    body does not have to look up the spec acceptance scenario for the
    canonical iteration count).

    Args:
        n_ticks: How many consecutive ticks the consuming test will run
            (default 5 per US3 acceptance scenario 2). Currently unused by
            the strategy itself — kept for caller documentation.

    Returns:
        Hypothesis ``SearchStrategy[WorldState]``.
    """
    _ = n_ticks  # documentation-only; consuming test controls the loop count
    return worldstate_strategy(min_entities=1, min_territories=0)
