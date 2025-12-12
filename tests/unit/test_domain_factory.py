"""Tests for DomainFactory.

TDD tests verifying the DomainFactory creates domain objects with correct defaults
and supports keyword argument overrides.
"""

import pytest
from tests.factories import DomainFactory

from babylon.models import EdgeType, SocialRole
from babylon.models.entities.social_class import IdeologicalProfile


class TestDomainFactoryWorker:
    """Tests for DomainFactory.create_worker()."""

    @pytest.fixture
    def factory(self) -> DomainFactory:
        """Create a DomainFactory instance."""
        return DomainFactory()

    def test_create_worker_default_id(self, factory: DomainFactory) -> None:
        """Worker has default id 'C001'."""
        worker = factory.create_worker()
        assert worker.id == "C001"

    def test_create_worker_default_name(self, factory: DomainFactory) -> None:
        """Worker has default name 'Test Worker'."""
        worker = factory.create_worker()
        assert worker.name == "Test Worker"

    def test_create_worker_default_role(self, factory: DomainFactory) -> None:
        """Worker has default role PERIPHERY_PROLETARIAT."""
        worker = factory.create_worker()
        assert worker.role == SocialRole.PERIPHERY_PROLETARIAT

    def test_create_worker_default_wealth(self, factory: DomainFactory) -> None:
        """Worker has default wealth 0.5."""
        worker = factory.create_worker()
        assert worker.wealth == 0.5

    def test_create_worker_default_ideology(self, factory: DomainFactory) -> None:
        """Worker has default ideology 0.0 (converted to IdeologicalProfile)."""
        worker = factory.create_worker()
        # Legacy ideology 0.0 converts to class_consciousness=0.5, national_identity=0.5
        expected = IdeologicalProfile.from_legacy_ideology(0.0)
        assert worker.ideology == expected

    def test_create_worker_default_organization(self, factory: DomainFactory) -> None:
        """Worker has default organization 0.1."""
        worker = factory.create_worker()
        assert worker.organization == 0.1

    def test_create_worker_default_repression(self, factory: DomainFactory) -> None:
        """Worker has default repression_faced 0.5."""
        worker = factory.create_worker()
        assert worker.repression_faced == 0.5

    def test_create_worker_default_subsistence(self, factory: DomainFactory) -> None:
        """Worker has default subsistence_threshold 0.3."""
        worker = factory.create_worker()
        assert worker.subsistence_threshold == 0.3

    def test_create_worker_override_wealth(self, factory: DomainFactory) -> None:
        """Worker wealth can be overridden."""
        worker = factory.create_worker(wealth=100.0)
        assert worker.wealth == 100.0

    def test_create_worker_override_id(self, factory: DomainFactory) -> None:
        """Worker id can be overridden."""
        worker = factory.create_worker(id="C999")
        assert worker.id == "C999"

    def test_create_worker_override_ideology(self, factory: DomainFactory) -> None:
        """Worker ideology can be overridden."""
        worker = factory.create_worker(ideology=-0.5)
        expected = IdeologicalProfile.from_legacy_ideology(-0.5)
        assert worker.ideology == expected


class TestDomainFactoryOwner:
    """Tests for DomainFactory.create_owner()."""

    @pytest.fixture
    def factory(self) -> DomainFactory:
        """Create a DomainFactory instance."""
        return DomainFactory()

    def test_create_owner_default_id(self, factory: DomainFactory) -> None:
        """Owner has default id 'C002'."""
        owner = factory.create_owner()
        assert owner.id == "C002"

    def test_create_owner_default_name(self, factory: DomainFactory) -> None:
        """Owner has default name 'Test Owner'."""
        owner = factory.create_owner()
        assert owner.name == "Test Owner"

    def test_create_owner_default_role(self, factory: DomainFactory) -> None:
        """Owner has default role CORE_BOURGEOISIE."""
        owner = factory.create_owner()
        assert owner.role == SocialRole.CORE_BOURGEOISIE

    def test_create_owner_default_wealth(self, factory: DomainFactory) -> None:
        """Owner has default wealth 10.0."""
        owner = factory.create_owner()
        assert owner.wealth == 10.0

    def test_create_owner_default_ideology(self, factory: DomainFactory) -> None:
        """Owner has default ideology 0.5 (converted to IdeologicalProfile)."""
        owner = factory.create_owner()
        expected = IdeologicalProfile.from_legacy_ideology(0.5)
        assert owner.ideology == expected

    def test_create_owner_default_organization(self, factory: DomainFactory) -> None:
        """Owner has default organization 0.7."""
        owner = factory.create_owner()
        assert owner.organization == 0.7

    def test_create_owner_default_repression(self, factory: DomainFactory) -> None:
        """Owner has default repression_faced 0.1."""
        owner = factory.create_owner()
        assert owner.repression_faced == 0.1

    def test_create_owner_default_subsistence(self, factory: DomainFactory) -> None:
        """Owner has default subsistence_threshold 0.1."""
        owner = factory.create_owner()
        assert owner.subsistence_threshold == 0.1

    def test_create_owner_override_wealth(self, factory: DomainFactory) -> None:
        """Owner wealth can be overridden."""
        owner = factory.create_owner(wealth=0.5)
        assert owner.wealth == 0.5

    def test_create_owner_override_organization(self, factory: DomainFactory) -> None:
        """Owner organization can be overridden."""
        owner = factory.create_owner(organization=0.8)
        assert owner.organization == 0.8


class TestDomainFactoryRelationship:
    """Tests for DomainFactory.create_relationship()."""

    @pytest.fixture
    def factory(self) -> DomainFactory:
        """Create a DomainFactory instance."""
        return DomainFactory()

    def test_create_relationship_default_source(self, factory: DomainFactory) -> None:
        """Relationship has default source_id 'C001'."""
        rel = factory.create_relationship()
        assert rel.source_id == "C001"

    def test_create_relationship_default_target(self, factory: DomainFactory) -> None:
        """Relationship has default target_id 'C002'."""
        rel = factory.create_relationship()
        assert rel.target_id == "C002"

    def test_create_relationship_default_type(self, factory: DomainFactory) -> None:
        """Relationship has default edge_type EXPLOITATION."""
        rel = factory.create_relationship()
        assert rel.edge_type == EdgeType.EXPLOITATION

    def test_create_relationship_default_value_flow(self, factory: DomainFactory) -> None:
        """Relationship has default value_flow 0.0."""
        rel = factory.create_relationship()
        assert rel.value_flow == 0.0

    def test_create_relationship_default_tension(self, factory: DomainFactory) -> None:
        """Relationship has default tension 0.0."""
        rel = factory.create_relationship()
        assert rel.tension == 0.0

    def test_create_relationship_override_type(self, factory: DomainFactory) -> None:
        """Relationship edge_type can be overridden."""
        rel = factory.create_relationship(edge_type=EdgeType.SOLIDARITY)
        assert rel.edge_type == EdgeType.SOLIDARITY


class TestDomainFactoryWorldState:
    """Tests for DomainFactory.create_world_state()."""

    @pytest.fixture
    def factory(self) -> DomainFactory:
        """Create a DomainFactory instance."""
        return DomainFactory()

    def test_create_world_state_default_tick(self, factory: DomainFactory) -> None:
        """WorldState has default tick 0."""
        state = factory.create_world_state()
        assert state.tick == 0

    def test_create_world_state_default_entities(self, factory: DomainFactory) -> None:
        """WorldState has default empty entities dict."""
        state = factory.create_world_state()
        assert state.entities == {}

    def test_create_world_state_default_relationships(self, factory: DomainFactory) -> None:
        """WorldState has default empty relationships list."""
        state = factory.create_world_state()
        assert state.relationships == []

    def test_create_world_state_default_event_log(self, factory: DomainFactory) -> None:
        """WorldState has default empty event_log."""
        state = factory.create_world_state()
        assert state.event_log == []

    def test_create_world_state_with_entities(self, factory: DomainFactory) -> None:
        """WorldState accepts entities dict."""
        worker = factory.create_worker()
        owner = factory.create_owner()
        state = factory.create_world_state(entities={"C001": worker, "C002": owner})
        assert len(state.entities) == 2
        assert "C001" in state.entities
        assert "C002" in state.entities

    def test_create_world_state_with_relationships(self, factory: DomainFactory) -> None:
        """WorldState accepts relationships list."""
        rel = factory.create_relationship()
        state = factory.create_world_state(relationships=[rel])
        assert len(state.relationships) == 1
        assert state.relationships[0].source_id == "C001"

    def test_create_world_state_override_tick(self, factory: DomainFactory) -> None:
        """WorldState tick can be overridden."""
        state = factory.create_world_state(tick=42)
        assert state.tick == 42


class TestDomainFactoryIntegration:
    """Integration tests for DomainFactory composing multiple entities."""

    @pytest.fixture
    def factory(self) -> DomainFactory:
        """Create a DomainFactory instance."""
        return DomainFactory()

    def test_create_two_node_state(self, factory: DomainFactory) -> None:
        """Factory can create a minimal two-node state."""
        worker = factory.create_worker()
        owner = factory.create_owner()
        rel = factory.create_relationship()
        state = factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[rel],
        )

        assert len(state.entities) == 2
        assert len(state.relationships) == 1
        assert state.entities["C001"].role == SocialRole.PERIPHERY_PROLETARIAT
        assert state.entities["C002"].role == SocialRole.CORE_BOURGEOISIE
        assert state.relationships[0].edge_type == EdgeType.EXPLOITATION

    def test_simulation_engine_fixture_equivalence(self, factory: DomainFactory) -> None:
        """Factory matches test_simulation_engine.py fixture values exactly.

        CRITICAL: The owner fixture in test_simulation_engine.py uses non-standard
        values that must be preserved via explicit overrides:
        - wealth=0.5 (default is 10.0)
        - ideology=0.0 (default is 0.5)
        - organization=0.8 (default is 0.7)
        """
        # Worker fixture from test_simulation_engine.py
        worker = factory.create_worker(
            name="Periphery Worker",
            # All other values match defaults
        )
        assert worker.id == "C001"
        assert worker.wealth == 0.5
        assert worker.organization == 0.1

        # Owner fixture from test_simulation_engine.py - requires overrides!
        owner = factory.create_owner(
            name="Core Owner",
            wealth=0.5,  # Override: test uses 0.5, not default 10.0
            ideology=0.0,  # Override: test uses 0.0, not default 0.5
            organization=0.8,  # Override: test uses 0.8, not default 0.7
        )
        assert owner.id == "C002"
        assert owner.wealth == 0.5
        assert owner.organization == 0.8
        # ideology=0.0 converts to class_consciousness=0.5
        expected_ideology = IdeologicalProfile.from_legacy_ideology(0.0)
        assert owner.ideology == expected_ideology
