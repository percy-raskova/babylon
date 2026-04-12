"""RED phase: Tests for Hypothesis strategies for simulation primitives.

Spec 040 Layer 2: Strategies generate valid SocialClass, Territory,
Relationship, and WorldState instances for property-based testing.
"""

from __future__ import annotations

from hypothesis import given, settings

from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.world_state import WorldState
from tests.property.strategies.primitives import (
    relationship_strategy,
    social_class_strategy,
    territory_strategy,
)
from tests.property.strategies.worldstate import worldstate_strategy


class TestPrimitiveStrategies:
    """Verify strategies produce valid domain objects."""

    @given(entity=social_class_strategy())
    @settings(max_examples=20, deadline=2000)
    def test_social_class_strategy_produces_valid_entity(self, entity: SocialClass) -> None:
        """Generated SocialClass instances pass Pydantic validation."""
        assert entity.id.startswith("C")
        assert len(entity.id) == 4
        assert entity.wealth >= 0.0
        assert 0.0 <= entity.organization <= 1.0

    @given(territory=territory_strategy())
    @settings(max_examples=20, deadline=2000)
    def test_territory_strategy_produces_valid_territory(self, territory: Territory) -> None:
        """Generated Territory instances pass Pydantic validation."""
        assert territory.id.startswith("T")
        assert len(territory.id) == 4
        assert 0.0 <= territory.heat <= 1.0

    @given(rel=relationship_strategy())
    @settings(max_examples=20, deadline=2000)
    def test_relationship_strategy_produces_valid_relationship(self, rel: Relationship) -> None:
        """Generated Relationship instances pass Pydantic validation."""
        assert rel.source_id != rel.target_id
        assert 0.0 <= rel.tension <= 1.0


class TestWorldStateStrategy:
    """Verify WorldState composite strategy."""

    @given(state=worldstate_strategy())
    @settings(max_examples=10, deadline=3000)
    def test_world_state_strategy_produces_valid_state(self, state: WorldState) -> None:
        """Generated WorldState instances pass Pydantic validation."""
        assert state.tick >= 0
        for eid, entity in state.entities.items():
            assert eid == entity.id
        for tid, territory in state.territories.items():
            assert tid == territory.id
