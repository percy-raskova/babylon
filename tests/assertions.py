"""Fluent assertion library for Babylon simulation tests.

This module provides a domain-specific assertion library that transforms
"math homework" assertions into "political narrative" assertions.

The BabylonAssert pattern enables expressive test assertions like::

    Assert(new_state).entity("C001").is_poorer_than(previous_state)
    Assert(state).relationship("C001", "C002").has_tension_increased(previous_state)

Instead of::

    initial_worker_wealth = previous_state.entities["C001"].wealth
    assert new_state.entities["C001"].wealth < initial_worker_wealth

The fluent API provides:
- Clear, readable test intent
- Rich error messages explaining failures
- Chainable assertions for multiple checks
- Proper handling of IdeologicalProfile vs legacy scalar ideology
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.models import Relationship, SocialClass, WorldState


class AssertionFailed(AssertionError):
    """Custom assertion error with rich context.

    This exception provides detailed error messages explaining
    what was expected vs what was found.
    """

    pass


class Assert:
    """Fluent assertion wrapper for WorldState.

    Provides entry point for all WorldState assertions.

    Example::

        Assert(state).tick_is(5)
        Assert(state).has_entity("C001")
        Assert(state).entity("C001").has_wealth(100.0)
        Assert(state).relationship("C001", "C002").has_tension_increased(previous)
    """

    def __init__(self, state: WorldState) -> None:
        """Initialize assertion wrapper.

        Args:
            state: WorldState to assert against.
        """
        self._state = state

    def tick_is(self, expected: int) -> Assert:
        """Assert that the tick counter equals expected value.

        Args:
            expected: Expected tick value.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If tick does not match expected.
        """
        if self._state.tick != expected:
            raise AssertionFailed(f"Expected tick to be {expected}, but was {self._state.tick}")
        return self

    def has_entity(self, entity_id: str) -> Assert:
        """Assert that an entity exists in the state.

        Args:
            entity_id: Entity ID to check for.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If entity does not exist.
        """
        if entity_id not in self._state.entities:
            available = list(self._state.entities.keys())
            raise AssertionFailed(
                f"Expected entity '{entity_id}' to exist in state, "
                f"but available entities are: {available}"
            )
        return self

    def entity(self, entity_id: str) -> EntityAssert:
        """Get fluent assertions for a specific entity.

        Args:
            entity_id: Entity ID to assert against.

        Returns:
            EntityAssert for the specified entity.

        Raises:
            AssertionFailed: If entity does not exist.
        """
        if entity_id not in self._state.entities:
            available = list(self._state.entities.keys())
            raise AssertionFailed(
                f"Cannot assert on entity '{entity_id}': "
                f"not found in state. Available entities: {available}"
            )
        return EntityAssert(self._state, entity_id)

    def relationship(self, source_id: str, target_id: str) -> RelationshipAssert:
        """Get fluent assertions for a specific relationship.

        Args:
            source_id: Source entity ID.
            target_id: Target entity ID.

        Returns:
            RelationshipAssert for the specified relationship.

        Raises:
            AssertionFailed: If relationship does not exist.
        """
        rel = _find_relationship(self._state, source_id, target_id)
        if rel is None:
            available = [f"({r.source_id} -> {r.target_id})" for r in self._state.relationships]
            raise AssertionFailed(
                f"Cannot assert on relationship ({source_id} -> {target_id}): "
                f"not found in state. Available relationships: {available}"
            )
        return RelationshipAssert(self._state, source_id, target_id)


class EntityAssert:
    """Fluent assertions for SocialClass entities.

    Provides domain-specific assertions for entity state:
    - Wealth comparisons (is_poorer_than, is_richer_than)
    - Ideology/consciousness checks (has_ideology, has_class_consciousness)
    - Survival probability assertions (has_p_acquiescence, has_p_revolution)

    Example::

        Assert(state).entity("C001").is_poorer_than(previous_state)
        Assert(state).entity("C001").has_wealth(0.5)
        Assert(state).entity("C001").consciousness_increased_from(previous_state)
    """

    def __init__(self, state: WorldState, entity_id: str) -> None:
        """Initialize entity assertion wrapper.

        Args:
            state: WorldState containing the entity.
            entity_id: ID of the entity to assert against.
        """
        self._state = state
        self._entity_id = entity_id

    @property
    def _entity(self) -> SocialClass:
        """Get the entity being asserted on."""
        return self._state.entities[self._entity_id]

    # =========================================================================
    # Wealth assertions
    # =========================================================================

    def has_wealth(self, value: float, tolerance: float = 0.001) -> EntityAssert:
        """Assert entity wealth equals expected value within tolerance.

        Args:
            value: Expected wealth value.
            tolerance: Acceptable difference (default: 0.001).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If wealth differs by more than tolerance.
        """
        actual = self._entity.wealth
        diff = abs(actual - value)
        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to have wealth {value} "
                f"(tolerance={tolerance}), but actual wealth is {actual} "
                f"(difference={diff:.6f})"
            )
        return self

    def is_poorer_than(self, previous_state: WorldState) -> EntityAssert:
        """Assert entity wealth decreased compared to previous state.

        Args:
            previous_state: Earlier WorldState to compare against.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If entity is not in previous state or wealth increased.
        """
        if self._entity_id not in previous_state.entities:
            raise AssertionFailed(
                f"Cannot compare wealth: Entity {self._entity_id} not found in previous state"
            )

        previous_wealth = previous_state.entities[self._entity_id].wealth
        current_wealth = self._entity.wealth

        if current_wealth >= previous_wealth:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to be poorer than previous state, "
                f"but wealth increased from {previous_wealth} to {current_wealth}"
            )
        return self

    def is_richer_than(self, previous_state: WorldState) -> EntityAssert:
        """Assert entity wealth increased compared to previous state.

        Args:
            previous_state: Earlier WorldState to compare against.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If entity is not in previous state or wealth decreased.
        """
        if self._entity_id not in previous_state.entities:
            raise AssertionFailed(
                f"Cannot compare wealth: Entity {self._entity_id} not found in previous state"
            )

        previous_wealth = previous_state.entities[self._entity_id].wealth
        current_wealth = self._entity.wealth

        if current_wealth <= previous_wealth:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to be richer than previous state, "
                f"but wealth decreased from {previous_wealth} to {current_wealth}"
            )
        return self

    def wealth_unchanged_from(
        self, previous_state: WorldState, tolerance: float = 0.001
    ) -> EntityAssert:
        """Assert entity wealth unchanged compared to previous state.

        Args:
            previous_state: Earlier WorldState to compare against.
            tolerance: Acceptable difference (default: 0.001).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If entity is not in previous state or wealth changed.
        """
        if self._entity_id not in previous_state.entities:
            raise AssertionFailed(
                f"Cannot compare wealth: Entity {self._entity_id} not found in previous state"
            )

        previous_wealth = previous_state.entities[self._entity_id].wealth
        current_wealth = self._entity.wealth
        diff = abs(current_wealth - previous_wealth)

        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} wealth to be unchanged, "
                f"but it changed from {previous_wealth} to {current_wealth} "
                f"(difference={diff:.6f}, tolerance={tolerance})"
            )
        return self

    # =========================================================================
    # Ideology assertions (IdeologicalProfile aware)
    # =========================================================================

    def has_ideology(self, expected: float, tolerance: float = 0.01) -> EntityAssert:
        """Assert entity legacy ideology equals expected value.

        Uses IdeologicalProfile.to_legacy_ideology() to convert the
        multi-dimensional ideology model to the legacy scalar [-1, 1].

        Args:
            expected: Expected legacy ideology value [-1, 1].
            tolerance: Acceptable difference (default: 0.01).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If ideology differs by more than tolerance.
        """
        actual = self._entity.ideology.to_legacy_ideology()
        diff = abs(actual - expected)
        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to have legacy ideology {expected} "
                f"(tolerance={tolerance}), but actual ideology is {actual} "
                f"(difference={diff:.6f})"
            )
        return self

    def has_class_consciousness(self, expected: float, tolerance: float = 0.01) -> EntityAssert:
        """Assert entity class consciousness equals expected value.

        Args:
            expected: Expected class consciousness value [0, 1].
            tolerance: Acceptable difference (default: 0.01).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If class consciousness differs by more than tolerance.
        """
        actual = self._entity.ideology.class_consciousness
        diff = abs(actual - expected)
        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to have class consciousness {expected} "
                f"(tolerance={tolerance}), but actual class consciousness is {actual} "
                f"(difference={diff:.6f})"
            )
        return self

    def consciousness_increased_from(self, previous_state: WorldState) -> EntityAssert:
        """Assert entity class consciousness increased compared to previous state.

        Args:
            previous_state: Earlier WorldState to compare against.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If consciousness did not increase.
        """
        if self._entity_id not in previous_state.entities:
            raise AssertionFailed(
                f"Cannot compare consciousness: Entity {self._entity_id} "
                f"not found in previous state"
            )

        previous = previous_state.entities[self._entity_id].ideology.class_consciousness
        current = self._entity.ideology.class_consciousness

        if current <= previous:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} class consciousness to increase, "
                f"but it went from {previous} to {current}"
            )
        return self

    def consciousness_decreased_from(self, previous_state: WorldState) -> EntityAssert:
        """Assert entity class consciousness decreased compared to previous state.

        Args:
            previous_state: Earlier WorldState to compare against.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If consciousness did not decrease.
        """
        if self._entity_id not in previous_state.entities:
            raise AssertionFailed(
                f"Cannot compare consciousness: Entity {self._entity_id} "
                f"not found in previous state"
            )

        previous = previous_state.entities[self._entity_id].ideology.class_consciousness
        current = self._entity.ideology.class_consciousness

        if current >= previous:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} class consciousness to decrease, "
                f"but it went from {previous} to {current}"
            )
        return self

    def consciousness_unchanged_from(
        self, previous_state: WorldState, tolerance: float = 0.001
    ) -> EntityAssert:
        """Assert entity class consciousness unchanged compared to previous state.

        Args:
            previous_state: Earlier WorldState to compare against.
            tolerance: Acceptable difference (default: 0.001).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If consciousness changed by more than tolerance.
        """
        if self._entity_id not in previous_state.entities:
            raise AssertionFailed(
                f"Cannot compare consciousness: Entity {self._entity_id} "
                f"not found in previous state"
            )

        previous = previous_state.entities[self._entity_id].ideology.class_consciousness
        current = self._entity.ideology.class_consciousness
        diff = abs(current - previous)

        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} class consciousness to be unchanged, "
                f"but it changed from {previous} to {current} "
                f"(difference={diff:.6f}, tolerance={tolerance})"
            )
        return self

    # =========================================================================
    # Survival probability assertions
    # =========================================================================

    def has_p_acquiescence(self, min_val: float) -> EntityAssert:
        """Assert entity P(S|A) is at least min_val.

        Args:
            min_val: Minimum expected acquiescence probability.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If P(S|A) is below min_val.
        """
        actual = self._entity.p_acquiescence
        if actual < min_val:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to have P(S|A) >= {min_val}, "
                f"but actual P(S|A) is {actual}"
            )
        return self

    def has_p_revolution(self, min_val: float) -> EntityAssert:
        """Assert entity P(S|R) is at least min_val.

        Args:
            min_val: Minimum expected revolution probability.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If P(S|R) is below min_val.
        """
        actual = self._entity.p_revolution
        if actual < min_val:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to have P(S|R) >= {min_val}, "
                f"but actual P(S|R) is {actual}"
            )
        return self

    def p_acquiescence_is(self, expected: float, tolerance: float = 0.01) -> EntityAssert:
        """Assert entity P(S|A) equals expected value within tolerance.

        Args:
            expected: Expected acquiescence probability.
            tolerance: Acceptable difference (default: 0.01).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If P(S|A) differs by more than tolerance.
        """
        actual = self._entity.p_acquiescence
        diff = abs(actual - expected)
        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to have P(S|A) = {expected} "
                f"(tolerance={tolerance}), but actual P(S|A) is {actual} "
                f"(difference={diff:.6f})"
            )
        return self

    def p_revolution_is(self, expected: float, tolerance: float = 0.01) -> EntityAssert:
        """Assert entity P(S|R) equals expected value within tolerance.

        Args:
            expected: Expected revolution probability.
            tolerance: Acceptable difference (default: 0.01).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If P(S|R) differs by more than tolerance.
        """
        actual = self._entity.p_revolution
        diff = abs(actual - expected)
        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Entity {self._entity_id} to have P(S|R) = {expected} "
                f"(tolerance={tolerance}), but actual P(S|R) is {actual} "
                f"(difference={diff:.6f})"
            )
        return self


class RelationshipAssert:
    """Fluent assertions for Relationship edges.

    Provides domain-specific assertions for relationship state:
    - Tension comparisons (has_tension_increased, tension_is)
    - Value flow checks (has_value_flow)

    Example::

        Assert(state).relationship("C001", "C002").has_tension_increased(previous)
        Assert(state).relationship("C001", "C002").has_value_flow(min_val=10.0)
    """

    def __init__(self, state: WorldState, source_id: str, target_id: str) -> None:
        """Initialize relationship assertion wrapper.

        Args:
            state: WorldState containing the relationship.
            source_id: Source entity ID.
            target_id: Target entity ID.
        """
        self._state = state
        self._source_id = source_id
        self._target_id = target_id

    @property
    def _relationship(self) -> Relationship:
        """Get the relationship being asserted on."""
        rel = _find_relationship(self._state, self._source_id, self._target_id)
        if rel is None:
            raise AssertionFailed(
                f"Relationship ({self._source_id} -> {self._target_id}) no longer exists in state"
            )
        return rel

    def has_tension_increased(self, previous_state: WorldState) -> RelationshipAssert:
        """Assert relationship tension increased compared to previous state.

        Args:
            previous_state: Earlier WorldState to compare against.

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If tension did not increase.
        """
        prev_rel = _find_relationship(previous_state, self._source_id, self._target_id)
        if prev_rel is None:
            raise AssertionFailed(
                f"Cannot compare tension: Relationship "
                f"({self._source_id} -> {self._target_id}) "
                f"not found in previous state"
            )

        previous_tension = prev_rel.tension
        current_tension = self._relationship.tension

        if current_tension <= previous_tension:
            raise AssertionFailed(
                f"Expected Relationship ({self._source_id} -> {self._target_id}) "
                f"tension to increase, but it went from {previous_tension} to {current_tension}"
            )
        return self

    def tension_is(self, expected: float, tolerance: float = 0.01) -> RelationshipAssert:
        """Assert relationship tension equals expected value.

        Args:
            expected: Expected tension value.
            tolerance: Acceptable difference (default: 0.01).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If tension differs by more than tolerance.
        """
        actual = self._relationship.tension
        diff = abs(actual - expected)
        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Relationship ({self._source_id} -> {self._target_id}) "
                f"to have tension {expected} (tolerance={tolerance}), "
                f"but actual tension is {actual} (difference={diff:.6f})"
            )
        return self

    def has_value_flow(self, min_val: float = 0.0) -> RelationshipAssert:
        """Assert relationship has value flow at least min_val.

        Args:
            min_val: Minimum expected value flow (default: 0.0 means any positive).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If value flow is below min_val.
        """
        actual = self._relationship.value_flow
        if min_val == 0.0:
            # Check for any positive value flow
            if actual <= 0:
                raise AssertionFailed(
                    f"Expected Relationship ({self._source_id} -> {self._target_id}) "
                    f"to have positive value flow, but actual value flow is {actual}"
                )
        elif actual < min_val:
            raise AssertionFailed(
                f"Expected Relationship ({self._source_id} -> {self._target_id}) "
                f"to have value flow >= {min_val}, but actual value flow is {actual}"
            )
        return self

    def value_flow_is(self, expected: float, tolerance: float = 0.01) -> RelationshipAssert:
        """Assert relationship value flow equals expected value.

        Args:
            expected: Expected value flow.
            tolerance: Acceptable difference (default: 0.01).

        Returns:
            Self for chaining.

        Raises:
            AssertionFailed: If value flow differs by more than tolerance.
        """
        actual = self._relationship.value_flow
        diff = abs(actual - expected)
        if diff > tolerance:
            raise AssertionFailed(
                f"Expected Relationship ({self._source_id} -> {self._target_id}) "
                f"to have value flow {expected} (tolerance={tolerance}), "
                f"but actual value flow is {actual} (difference={diff:.6f})"
            )
        return self


def _find_relationship(state: WorldState, source_id: str, target_id: str) -> Relationship | None:
    """Find a relationship by source and target IDs.

    Args:
        state: WorldState to search.
        source_id: Source entity ID.
        target_id: Target entity ID.

    Returns:
        Relationship if found, None otherwise.
    """
    for rel in state.relationships:
        if rel.source_id == source_id and rel.target_id == target_id:
            return rel
    return None
