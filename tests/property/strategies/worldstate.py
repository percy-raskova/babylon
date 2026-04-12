"""Hypothesis strategy for generating valid WorldState instances.

Spec 040 Layer 2: Composite strategy that composes primitives into
a valid WorldState, ensuring referential integrity.
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from babylon.models.world_state import WorldState
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
