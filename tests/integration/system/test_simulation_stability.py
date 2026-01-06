"""Stability tests for simulation engine over long tick runs.

These tests verify that the simulation maintains valid bounds and deterministic
behavior over hundreds or thousands of ticks. They are intentionally slow
(~15-30s each) and should NOT run during pre-commit.

Moved from tests/unit/engine/test_simulation_engine.py for performance reasons.
"""

import pytest

from babylon.engine.simulation_engine import step
from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    SocialClass,
    SocialRole,
    WorldState,
)
from tests.factories import DomainFactory

# =============================================================================
# FIXTURES
# =============================================================================

_factory = DomainFactory()


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return _factory.create_worker(name="Periphery Worker")


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class."""
    return _factory.create_owner(
        name="Core Owner",
        wealth=0.5,
        ideology=0.0,
        organization=0.8,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return _factory.create_relationship()


@pytest.fixture
def two_node_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create a minimal WorldState with two nodes and one edge."""
    return _factory.create_world_state(
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


# =============================================================================
# DETERMINISM STABILITY TESTS
# =============================================================================


@pytest.mark.slow
@pytest.mark.integration
class TestSimulationDeterminism:
    """Verify simulation produces identical results across multiple runs."""

    def test_hundred_turns_deterministic(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """100 turns produce identical results.

        This test verifies that the simulation engine is fully deterministic -
        running the same starting state twice produces bit-identical results.
        """
        # Run 1
        result1 = two_node_state
        for _ in range(100):
            result1 = step(result1, config)

        # Run 2 (same starting state)
        result2 = two_node_state
        for _ in range(100):
            result2 = step(result2, config)

        # Compare final states
        assert result1.tick == result2.tick == 100
        assert result1.entities["C001"].wealth == pytest.approx(result2.entities["C001"].wealth)
        assert result1.entities["C002"].wealth == pytest.approx(result2.entities["C002"].wealth)
        # Compare class_consciousness from IdeologicalProfile
        assert result1.entities["C001"].ideology.class_consciousness == pytest.approx(
            result2.entities["C001"].ideology.class_consciousness
        )


# =============================================================================
# BOUNDS STABILITY TESTS
# =============================================================================


@pytest.mark.slow
@pytest.mark.integration
class TestConsciousnessBoundsStability:
    """Verify class_consciousness stays within [0, 1] over long simulations."""

    def test_ideology_clamped_lower_bound(
        self,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """Class consciousness cannot exceed 1.0 even over 1000 ticks.

        The class_consciousness field is constrained to [0, 1]. Even with continuous
        drift, it must be clamped to prevent validation errors.
        """
        # Start already revolutionary to stress test the upper bound
        revolutionary_worker = SocialClass(
            id="C001",
            name="Revolutionary Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=-0.9,  # Already very revolutionary (consciousness 0.95)
            organization=0.1,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )
        state = WorldState(
            tick=0,
            entities={"C001": revolutionary_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        # Run 1000 ticks
        for _ in range(1000):
            state = step(state, config)

        # Class consciousness must stay <= 1.0
        assert state.entities["C001"].ideology.class_consciousness <= 1.0

    def test_ideology_clamped_upper_bound(
        self,
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """Class consciousness cannot go below 0.0 (use labor aristocrat scenario).

        A labor aristocrat receiving more than they produce should have
        consciousness decay, but class_consciousness must stay >= 0.0.
        """
        # Labor aristocrat with low (reactionary) consciousness
        labor_aristocrat = SocialClass(
            id="C001",
            name="Labor Aristocrat",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=0.9,  # High wages
            ideology=0.9,  # Already very reactionary (consciousness 0.05)
            organization=0.1,
            repression_faced=0.1,
            subsistence_threshold=0.3,
        )
        # Labor aristocrat exploiting periphery
        exploitation_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )
        state = WorldState(
            tick=0,
            entities={"C001": labor_aristocrat, "C002": owner},
            relationships=[exploitation_edge],
        )

        # Run 1000 ticks
        for _ in range(1000):
            state = step(state, config)

        # Class consciousness must stay >= 0.0
        assert state.entities["C001"].ideology.class_consciousness >= 0.0

    def test_thousand_tick_stability(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Class consciousness stays bounded [0, 1] over 1000 ticks.

        This is a stability test to ensure no numerical drift causes
        consciousness to escape valid bounds over long simulations.
        """
        state = two_node_state
        for _ in range(1000):
            state = step(state, config)

        # All class consciousness values must be in valid range
        for entity_id, entity in state.entities.items():
            consciousness = entity.ideology.class_consciousness
            assert 0.0 <= consciousness <= 1.0, (
                f"Entity {entity_id} class_consciousness {consciousness} out of bounds"
            )
