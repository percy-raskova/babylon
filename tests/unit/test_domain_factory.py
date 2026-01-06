"""Tests for DomainFactory.

TDD tests verifying the DomainFactory creates domain objects with correct defaults
and supports keyword argument overrides.

Refactored with pytest.parametrize for Phase 4 of Unit Test Health Improvement Plan.
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

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("id", "C001"),
            ("name", "Test Worker"),
            ("role", SocialRole.PERIPHERY_PROLETARIAT),
            ("wealth", 0.5),
            ("organization", 0.1),
            ("repression_faced", 0.5),
            ("subsistence_threshold", 0.3),
        ],
        ids=[
            "default_id",
            "default_name",
            "default_role",
            "default_wealth",
            "default_organization",
            "default_repression",
            "default_subsistence",
        ],
    )
    def test_create_worker_defaults(
        self, factory: DomainFactory, attr: str, expected: object
    ) -> None:
        """Worker has correct default values."""
        worker = factory.create_worker()
        assert getattr(worker, attr) == expected

    def test_create_worker_default_ideology(self, factory: DomainFactory) -> None:
        """Worker has default ideology 0.0 (converted to IdeologicalProfile)."""
        worker = factory.create_worker()
        # Legacy ideology 0.0 converts to class_consciousness=0.5, national_identity=0.5
        expected = IdeologicalProfile.from_legacy_ideology(0.0)
        assert worker.ideology == expected

    @pytest.mark.parametrize(
        "kwarg,value,attr",
        [
            ({"wealth": 100.0}, 100.0, "wealth"),
            ({"id": "C999"}, "C999", "id"),
        ],
        ids=["override_wealth", "override_id"],
    )
    def test_create_worker_override(
        self, factory: DomainFactory, kwarg: dict, value: object, attr: str
    ) -> None:
        """Worker attributes can be overridden."""
        worker = factory.create_worker(**kwarg)
        assert getattr(worker, attr) == value

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

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("id", "C002"),
            ("name", "Test Owner"),
            ("role", SocialRole.CORE_BOURGEOISIE),
            ("wealth", 10.0),
            ("organization", 0.7),
            ("repression_faced", 0.1),
            ("subsistence_threshold", 0.1),
        ],
        ids=[
            "default_id",
            "default_name",
            "default_role",
            "default_wealth",
            "default_organization",
            "default_repression",
            "default_subsistence",
        ],
    )
    def test_create_owner_defaults(
        self, factory: DomainFactory, attr: str, expected: object
    ) -> None:
        """Owner has correct default values."""
        owner = factory.create_owner()
        assert getattr(owner, attr) == expected

    def test_create_owner_default_ideology(self, factory: DomainFactory) -> None:
        """Owner has default ideology 0.5 (converted to IdeologicalProfile)."""
        owner = factory.create_owner()
        expected = IdeologicalProfile.from_legacy_ideology(0.5)
        assert owner.ideology == expected

    @pytest.mark.parametrize(
        "kwarg,value,attr",
        [
            ({"wealth": 0.5}, 0.5, "wealth"),
            ({"organization": 0.8}, 0.8, "organization"),
        ],
        ids=["override_wealth", "override_organization"],
    )
    def test_create_owner_override(
        self, factory: DomainFactory, kwarg: dict, value: object, attr: str
    ) -> None:
        """Owner attributes can be overridden."""
        owner = factory.create_owner(**kwarg)
        assert getattr(owner, attr) == value


class TestDomainFactoryRelationship:
    """Tests for DomainFactory.create_relationship()."""

    @pytest.fixture
    def factory(self) -> DomainFactory:
        """Create a DomainFactory instance."""
        return DomainFactory()

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("source_id", "C001"),
            ("target_id", "C002"),
            ("edge_type", EdgeType.EXPLOITATION),
            ("value_flow", 0.0),
            ("tension", 0.0),
        ],
        ids=[
            "default_source",
            "default_target",
            "default_type",
            "default_value_flow",
            "default_tension",
        ],
    )
    def test_create_relationship_defaults(
        self, factory: DomainFactory, attr: str, expected: object
    ) -> None:
        """Relationship has correct default values."""
        rel = factory.create_relationship()
        assert getattr(rel, attr) == expected

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

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("tick", 0),
            ("entities", {}),
            ("relationships", []),
            ("event_log", []),
        ],
        ids=["default_tick", "default_entities", "default_relationships", "default_event_log"],
    )
    def test_create_world_state_defaults(
        self, factory: DomainFactory, attr: str, expected: object
    ) -> None:
        """WorldState has correct default values."""
        state = factory.create_world_state()
        assert getattr(state, attr) == expected

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
