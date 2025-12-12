"""Tests for the BabylonAssert fluent assertion library.

TDD tests verifying the behavior of the Assert, EntityAssert, and
RelationshipAssert classes in tests/assertions.py.

Each test class covers a specific aspect of the assertion library:
- TestAssertEntry: Entry point and state-level assertions
- TestEntityWealth: Entity wealth comparison assertions
- TestEntityIdeology: Entity ideology/consciousness assertions
- TestEntitySurvival: Entity survival probability assertions
- TestRelationship: Relationship tension and value flow assertions
- TestChaining: Fluent chaining behavior
- TestErrorMessages: Error message quality
"""

import pytest
from tests.assertions import Assert, AssertionFailed, EntityAssert, RelationshipAssert
from tests.factories import DomainFactory

from babylon.models import (
    EdgeType,
    Relationship,
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.entities.social_class import IdeologicalProfile

# =============================================================================
# FIXTURES
# =============================================================================

_factory = DomainFactory()


@pytest.fixture
def worker() -> SocialClass:
    """Create a worker entity."""
    return _factory.create_worker(wealth=0.5, ideology=0.0)


@pytest.fixture
def wealthy_worker() -> SocialClass:
    """Create a wealthy worker entity."""
    return _factory.create_worker(wealth=0.8, ideology=0.0)


@pytest.fixture
def owner() -> SocialClass:
    """Create an owner entity."""
    return _factory.create_owner(wealth=10.0, ideology=0.5)


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship."""
    return _factory.create_relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=5.0,
        tension=0.1,
    )


@pytest.fixture
def basic_state(
    worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
) -> WorldState:
    """Create a basic two-node state."""
    return _factory.create_world_state(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


# =============================================================================
# ENTRY POINT TESTS
# =============================================================================


@pytest.mark.unit
class TestAssertEntry:
    """Tests for Assert class entry point and state-level assertions."""

    def test_assert_creates_wrapper(self, basic_state: WorldState) -> None:
        """Assert() returns an Assert instance."""
        result = Assert(basic_state)
        assert isinstance(result, Assert)

    def test_tick_is_passes_when_correct(self, basic_state: WorldState) -> None:
        """tick_is() passes when tick matches."""
        Assert(basic_state).tick_is(0)  # Should not raise

    def test_tick_is_fails_when_incorrect(self, basic_state: WorldState) -> None:
        """tick_is() raises AssertionFailed when tick does not match."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).tick_is(5)
        assert "Expected tick to be 5" in str(exc_info.value)
        assert "was 0" in str(exc_info.value)

    def test_has_entity_passes_when_exists(self, basic_state: WorldState) -> None:
        """has_entity() passes when entity exists."""
        Assert(basic_state).has_entity("C001")  # Should not raise

    def test_has_entity_fails_when_missing(self, basic_state: WorldState) -> None:
        """has_entity() raises AssertionFailed when entity does not exist."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).has_entity("C999")
        assert "C999" in str(exc_info.value)
        assert "C001" in str(exc_info.value)  # Shows available entities

    def test_entity_returns_entity_assert(self, basic_state: WorldState) -> None:
        """entity() returns EntityAssert for existing entity."""
        result = Assert(basic_state).entity("C001")
        assert isinstance(result, EntityAssert)

    def test_entity_raises_when_missing(self, basic_state: WorldState) -> None:
        """entity() raises AssertionFailed when entity does not exist."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).entity("C999")
        assert "C999" in str(exc_info.value)

    def test_relationship_returns_relationship_assert(self, basic_state: WorldState) -> None:
        """relationship() returns RelationshipAssert for existing relationship."""
        result = Assert(basic_state).relationship("C001", "C002")
        assert isinstance(result, RelationshipAssert)

    def test_relationship_raises_when_missing(self, basic_state: WorldState) -> None:
        """relationship() raises AssertionFailed when relationship does not exist."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).relationship("C002", "C001")  # Wrong direction
        assert "C002" in str(exc_info.value)
        assert "C001" in str(exc_info.value)


# =============================================================================
# ENTITY WEALTH TESTS
# =============================================================================


@pytest.mark.unit
class TestEntityWealth:
    """Tests for EntityAssert wealth comparison methods."""

    def test_has_wealth_passes_within_tolerance(self, basic_state: WorldState) -> None:
        """has_wealth() passes when wealth is within tolerance."""
        Assert(basic_state).entity("C001").has_wealth(0.5)  # Should not raise

    def test_has_wealth_passes_within_custom_tolerance(self, basic_state: WorldState) -> None:
        """has_wealth() passes within custom tolerance."""
        Assert(basic_state).entity("C001").has_wealth(0.51, tolerance=0.02)

    def test_has_wealth_fails_outside_tolerance(self, basic_state: WorldState) -> None:
        """has_wealth() raises AssertionFailed when wealth differs."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).entity("C001").has_wealth(1.0)
        assert "C001" in str(exc_info.value)
        assert "0.5" in str(exc_info.value)
        assert "1.0" in str(exc_info.value)

    def test_is_poorer_than_passes_when_wealth_decreased(
        self, worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
    ) -> None:
        """is_poorer_than() passes when wealth decreased."""
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        # Create state with reduced worker wealth
        poorer_worker = SocialClass(
            id="C001",
            name="Test Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.3,  # Reduced from 0.5
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": poorer_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        Assert(later_state).entity("C001").is_poorer_than(initial_state)

    def test_is_poorer_than_fails_when_wealth_increased(
        self, worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
    ) -> None:
        """is_poorer_than() raises AssertionFailed when wealth increased."""
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        # Create state with increased worker wealth
        richer_worker = SocialClass(
            id="C001",
            name="Test Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.6,  # Increased from 0.5
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": richer_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(later_state).entity("C001").is_poorer_than(initial_state)
        assert "C001" in str(exc_info.value)
        assert "0.5" in str(exc_info.value)
        assert "0.6" in str(exc_info.value)
        assert "increased" in str(exc_info.value)

    def test_is_richer_than_passes_when_wealth_increased(
        self, worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
    ) -> None:
        """is_richer_than() passes when wealth increased."""
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        richer_worker = SocialClass(
            id="C001",
            name="Test Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.7,  # Increased from 0.5
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": richer_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        Assert(later_state).entity("C001").is_richer_than(initial_state)

    def test_is_richer_than_fails_when_wealth_decreased(
        self, worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
    ) -> None:
        """is_richer_than() raises AssertionFailed when wealth decreased."""
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        poorer_worker = SocialClass(
            id="C001",
            name="Test Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.3,  # Decreased from 0.5
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": poorer_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(later_state).entity("C001").is_richer_than(initial_state)
        assert "C001" in str(exc_info.value)
        assert "decreased" in str(exc_info.value)

    def test_wealth_unchanged_from_passes_when_unchanged(self, basic_state: WorldState) -> None:
        """wealth_unchanged_from() passes when wealth is the same."""
        Assert(basic_state).entity("C001").wealth_unchanged_from(basic_state)

    def test_wealth_unchanged_from_fails_when_changed(
        self, worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
    ) -> None:
        """wealth_unchanged_from() raises AssertionFailed when wealth changed."""
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        changed_worker = SocialClass(
            id="C001",
            name="Test Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.6,
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": changed_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(later_state).entity("C001").wealth_unchanged_from(initial_state)
        assert "unchanged" in str(exc_info.value)


# =============================================================================
# ENTITY IDEOLOGY TESTS
# =============================================================================


@pytest.mark.unit
class TestEntityIdeology:
    """Tests for EntityAssert ideology/consciousness methods.

    These tests verify proper handling of IdeologicalProfile objects,
    including conversion to legacy scalar ideology via to_legacy_ideology().
    """

    def test_has_ideology_converts_ideological_profile(self, basic_state: WorldState) -> None:
        """has_ideology() uses to_legacy_ideology() for comparison."""
        # Worker has ideology=0.0 which maps to:
        # class_consciousness=0.5, national_identity=0.5
        # to_legacy_ideology() = 1 - 2*0.5 = 0.0
        Assert(basic_state).entity("C001").has_ideology(0.0)

    def test_has_ideology_fails_when_different(self, basic_state: WorldState) -> None:
        """has_ideology() raises AssertionFailed when ideology differs."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).entity("C001").has_ideology(-0.5)
        assert "C001" in str(exc_info.value)
        assert "ideology" in str(exc_info.value).lower()

    def test_has_class_consciousness_passes_when_correct(self, owner: SocialClass) -> None:
        """has_class_consciousness() works with IdeologicalProfile."""
        # Owner has ideology=0.5 which maps to class_consciousness=0.25
        state = _factory.create_world_state(
            entities={"C002": owner},
            relationships=[],
        )
        Assert(state).entity("C002").has_class_consciousness(0.25)

    def test_has_class_consciousness_fails_when_different(self, basic_state: WorldState) -> None:
        """has_class_consciousness() raises when value differs."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).entity("C001").has_class_consciousness(0.9)
        assert "C001" in str(exc_info.value)
        assert "consciousness" in str(exc_info.value).lower()

    def test_consciousness_increased_from_passes(self, owner: SocialClass) -> None:
        """consciousness_increased_from() passes when consciousness rose."""
        # Initial low consciousness worker
        worker_low = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.3, national_identity=0.5),
        )
        initial_state = _factory.create_world_state(
            entities={"C001": worker_low, "C002": owner},
        )

        # Later with higher consciousness
        worker_high = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.6, national_identity=0.5),
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": worker_high, "C002": owner},
        )

        Assert(later_state).entity("C001").consciousness_increased_from(initial_state)

    def test_consciousness_increased_from_fails_when_decreased(self, owner: SocialClass) -> None:
        """consciousness_increased_from() raises when consciousness fell."""
        worker_high = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.8, national_identity=0.5),
        )
        initial_state = _factory.create_world_state(
            entities={"C001": worker_high, "C002": owner},
        )

        worker_low = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.4, national_identity=0.5),
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": worker_low, "C002": owner},
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(later_state).entity("C001").consciousness_increased_from(initial_state)
        assert "C001" in str(exc_info.value)
        assert "0.8" in str(exc_info.value)
        assert "0.4" in str(exc_info.value)

    def test_consciousness_unchanged_from_passes_when_same(self, basic_state: WorldState) -> None:
        """consciousness_unchanged_from() passes when consciousness is same."""
        Assert(basic_state).entity("C001").consciousness_unchanged_from(basic_state)

    def test_consciousness_unchanged_from_fails_when_different(self, owner: SocialClass) -> None:
        """consciousness_unchanged_from() raises when consciousness differs."""
        worker_low = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.3, national_identity=0.5),
        )
        initial_state = _factory.create_world_state(
            entities={"C001": worker_low, "C002": owner},
        )

        worker_high = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.6, national_identity=0.5),
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": worker_high, "C002": owner},
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(later_state).entity("C001").consciousness_unchanged_from(initial_state)
        assert "unchanged" in str(exc_info.value)


# =============================================================================
# ENTITY SURVIVAL TESTS
# =============================================================================


@pytest.mark.unit
class TestEntitySurvival:
    """Tests for EntityAssert survival probability methods."""

    def test_has_p_acquiescence_passes_when_above_min(self) -> None:
        """has_p_acquiescence() passes when P(S|A) >= min_val."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_acquiescence=0.7,
        )
        state = _factory.create_world_state(entities={"C001": worker})

        Assert(state).entity("C001").has_p_acquiescence(0.5)

    def test_has_p_acquiescence_fails_when_below_min(self) -> None:
        """has_p_acquiescence() raises when P(S|A) < min_val."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_acquiescence=0.3,
        )
        state = _factory.create_world_state(entities={"C001": worker})

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(state).entity("C001").has_p_acquiescence(0.5)
        assert "P(S|A)" in str(exc_info.value)
        assert "0.5" in str(exc_info.value)
        assert "0.3" in str(exc_info.value)

    def test_has_p_revolution_passes_when_above_min(self) -> None:
        """has_p_revolution() passes when P(S|R) >= min_val."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_revolution=0.6,
        )
        state = _factory.create_world_state(entities={"C001": worker})

        Assert(state).entity("C001").has_p_revolution(0.4)

    def test_has_p_revolution_fails_when_below_min(self) -> None:
        """has_p_revolution() raises when P(S|R) < min_val."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_revolution=0.2,
        )
        state = _factory.create_world_state(entities={"C001": worker})

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(state).entity("C001").has_p_revolution(0.5)
        assert "P(S|R)" in str(exc_info.value)

    def test_p_acquiescence_is_passes_within_tolerance(self) -> None:
        """p_acquiescence_is() passes when within tolerance."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_acquiescence=0.5,
        )
        state = _factory.create_world_state(entities={"C001": worker})

        Assert(state).entity("C001").p_acquiescence_is(0.5)

    def test_p_revolution_is_passes_within_tolerance(self) -> None:
        """p_revolution_is() passes when within tolerance."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_revolution=0.5,
        )
        state = _factory.create_world_state(entities={"C001": worker})

        Assert(state).entity("C001").p_revolution_is(0.5)


# =============================================================================
# RELATIONSHIP TESTS
# =============================================================================


@pytest.mark.unit
class TestRelationship:
    """Tests for RelationshipAssert tension and value flow methods."""

    def test_has_tension_increased_passes_when_increased(
        self, worker: SocialClass, owner: SocialClass
    ) -> None:
        """has_tension_increased() passes when tension rose."""
        low_tension_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.1,
        )
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[low_tension_edge],
        )

        high_tension_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.5,
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": worker, "C002": owner},
            relationships=[high_tension_edge],
        )

        Assert(later_state).relationship("C001", "C002").has_tension_increased(initial_state)

    def test_has_tension_increased_fails_when_decreased(
        self, worker: SocialClass, owner: SocialClass
    ) -> None:
        """has_tension_increased() raises when tension fell."""
        high_tension_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.5,
        )
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[high_tension_edge],
        )

        low_tension_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.2,
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": worker, "C002": owner},
            relationships=[low_tension_edge],
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(later_state).relationship("C001", "C002").has_tension_increased(initial_state)
        assert "0.5" in str(exc_info.value)
        assert "0.2" in str(exc_info.value)

    def test_tension_is_passes_within_tolerance(self, basic_state: WorldState) -> None:
        """tension_is() passes when within tolerance."""
        Assert(basic_state).relationship("C001", "C002").tension_is(0.1)

    def test_tension_is_fails_outside_tolerance(self, basic_state: WorldState) -> None:
        """tension_is() raises when outside tolerance."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).relationship("C001", "C002").tension_is(0.5)
        assert "tension" in str(exc_info.value).lower()

    def test_has_value_flow_passes_when_positive(self, basic_state: WorldState) -> None:
        """has_value_flow() passes when value flow is positive."""
        Assert(basic_state).relationship("C001", "C002").has_value_flow()

    def test_has_value_flow_passes_when_above_min(self, basic_state: WorldState) -> None:
        """has_value_flow() passes when value flow >= min_val."""
        Assert(basic_state).relationship("C001", "C002").has_value_flow(min_val=3.0)

    def test_has_value_flow_fails_when_below_min(self, basic_state: WorldState) -> None:
        """has_value_flow() raises when value flow < min_val."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).relationship("C001", "C002").has_value_flow(min_val=10.0)
        assert "value flow" in str(exc_info.value).lower()

    def test_has_value_flow_fails_when_zero(self, worker: SocialClass, owner: SocialClass) -> None:
        """has_value_flow() raises when value flow is zero."""
        zero_flow_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
        )
        state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[zero_flow_edge],
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(state).relationship("C001", "C002").has_value_flow()
        assert "positive" in str(exc_info.value)

    def test_value_flow_is_passes_within_tolerance(self, basic_state: WorldState) -> None:
        """value_flow_is() passes when within tolerance."""
        Assert(basic_state).relationship("C001", "C002").value_flow_is(5.0)

    def test_value_flow_is_fails_outside_tolerance(self, basic_state: WorldState) -> None:
        """value_flow_is() raises when outside tolerance."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).relationship("C001", "C002").value_flow_is(10.0)
        assert "value flow" in str(exc_info.value).lower()


# =============================================================================
# CHAINING TESTS
# =============================================================================


@pytest.mark.unit
class TestChaining:
    """Tests for fluent method chaining."""

    def test_assert_methods_return_self(self, basic_state: WorldState) -> None:
        """Assert methods return self for chaining."""
        result = Assert(basic_state).tick_is(0).has_entity("C001")
        assert isinstance(result, Assert)

    def test_entity_methods_return_self(self, basic_state: WorldState) -> None:
        """EntityAssert methods return self for chaining."""
        result = Assert(basic_state).entity("C001").has_wealth(0.5).has_ideology(0.0)
        assert isinstance(result, EntityAssert)

    def test_relationship_methods_return_self(self, basic_state: WorldState) -> None:
        """RelationshipAssert methods return self for chaining."""
        result = Assert(basic_state).relationship("C001", "C002").tension_is(0.1).has_value_flow()
        assert isinstance(result, RelationshipAssert)

    def test_complex_chaining(self, basic_state: WorldState) -> None:
        """Complex chaining works correctly."""
        Assert(basic_state).tick_is(0).has_entity("C001").has_entity("C002")
        Assert(basic_state).entity("C001").has_wealth(0.5).has_ideology(0.0)
        Assert(basic_state).relationship("C001", "C002").tension_is(0.1).has_value_flow()


# =============================================================================
# ERROR MESSAGE TESTS
# =============================================================================


@pytest.mark.unit
class TestErrorMessages:
    """Tests for error message quality and readability."""

    def test_is_poorer_than_error_message_is_readable(
        self, worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
    ) -> None:
        """is_poorer_than() produces readable error message."""
        initial_state = _factory.create_world_state(
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        richer_worker = SocialClass(
            id="C001",
            name="Test Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.6,
        )
        later_state = _factory.create_world_state(
            tick=1,
            entities={"C001": richer_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        with pytest.raises(AssertionFailed) as exc_info:
            Assert(later_state).entity("C001").is_poorer_than(initial_state)

        error_msg = str(exc_info.value)
        # Should mention the entity
        assert "C001" in error_msg
        # Should mention both wealth values
        assert "0.5" in error_msg
        assert "0.6" in error_msg
        # Should explain the direction
        assert "increased" in error_msg

    def test_entity_not_found_shows_available(self, basic_state: WorldState) -> None:
        """Entity not found error shows available entities."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).entity("C999")

        error_msg = str(exc_info.value)
        assert "C999" in error_msg
        assert "C001" in error_msg
        assert "C002" in error_msg

    def test_relationship_not_found_shows_available(self, basic_state: WorldState) -> None:
        """Relationship not found error shows available relationships."""
        with pytest.raises(AssertionFailed) as exc_info:
            Assert(basic_state).relationship("C002", "C001")

        error_msg = str(exc_info.value)
        assert "C001 -> C002" in error_msg
