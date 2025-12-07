"""Tests for the Contradiction Engine - the dialectical heart of Babylon.

These tests verify the mathematical correctness of class struggle simulation.
Following TDD: Red -> Green -> Refactor.

Test Categories:
1. Tension Mechanics - accumulation, bounds, phase transitions
2. Resolution - synthesis, rupture, suppression outcomes
3. Propagation - how contradictions affect each other
4. Two-Object Interaction - the minimal viable dialectic
"""

import pytest

from babylon.systems.contradiction_analysis import (
    ContradictionAnalysis,
    ContradictionState,
)


class TestContradictionStateCreation:
    """Tests for creating and validating contradiction states."""

    def test_create_basic_contradiction(self) -> None:
        """A contradiction can be created with required fields."""
        state = ContradictionState(
            id="labor_capital",
            name="Labor vs Capital",
            thesis="Capitalist accumulation",
            antithesis="Worker exploitation",
        )

        assert state.id == "labor_capital"
        assert state.name == "Labor vs Capital"
        assert state.tension == 0.0
        assert state.momentum == 0.0
        assert state.resolved is False

    def test_tension_must_be_bounded(self) -> None:
        """Tension must be between 0.0 and 1.0 (compact manifold)."""
        # Valid tension
        state = ContradictionState(
            id="test",
            name="Test",
            thesis="A",
            antithesis="B",
            tension=0.5,
        )
        assert state.tension == 0.5

        # Invalid tension should raise
        with pytest.raises(ValueError):
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                tension=1.5,  # Out of bounds
            )

    def test_momentum_must_be_bounded(self) -> None:
        """Momentum must be between -1.0 and 1.0."""
        state = ContradictionState(
            id="test",
            name="Test",
            thesis="A",
            antithesis="B",
            momentum=-0.5,
        )
        assert state.momentum == -0.5

        with pytest.raises(ValueError):
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                momentum=2.0,  # Out of bounds
            )


class TestContradictionAnalysisBasics:
    """Tests for the ContradictionAnalysis system basics."""

    def test_register_contradiction(self) -> None:
        """Contradictions can be registered in the system."""
        engine = ContradictionAnalysis()
        state = ContradictionState(
            id="labor_capital",
            name="Labor vs Capital",
            thesis="Accumulation",
            antithesis="Exploitation",
        )

        engine.register_contradiction(state)

        retrieved = engine.get_contradiction("labor_capital")
        assert retrieved is not None
        assert retrieved.name == "Labor vs Capital"

    def test_get_nonexistent_contradiction_returns_none(self) -> None:
        """Getting a non-existent contradiction returns None, not error."""
        engine = ContradictionAnalysis()
        result = engine.get_contradiction("does_not_exist")
        assert result is None


class TestTensionMechanics:
    """Tests for tension accumulation and bounds."""

    def test_increase_tension(self) -> None:
        """Tension can be increased via update_tension."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                tension=0.3,
            )
        )

        engine.update_tension("test", delta=0.2)

        state = engine.get_contradiction("test")
        assert state is not None
        assert state.tension == pytest.approx(0.5, abs=0.001)

    def test_decrease_tension(self) -> None:
        """Tension can be decreased via negative delta."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                tension=0.5,
            )
        )

        engine.update_tension("test", delta=-0.2)

        state = engine.get_contradiction("test")
        assert state is not None
        assert state.tension == pytest.approx(0.3, abs=0.001)

    def test_tension_cannot_exceed_one(self) -> None:
        """Tension is clamped at 1.0 (compact space boundary)."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                tension=0.9,
            )
        )

        # Try to exceed 1.0
        engine.update_tension("test", delta=0.5)

        state = engine.get_contradiction("test")
        assert state is not None
        assert state.tension == 1.0  # Clamped, not 1.4

    def test_tension_cannot_go_negative(self) -> None:
        """Tension is clamped at 0.0."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                tension=0.2,
            )
        )

        engine.update_tension("test", delta=-0.5)

        state = engine.get_contradiction("test")
        assert state is not None
        assert state.tension == 0.0  # Clamped, not -0.3

    def test_momentum_tracks_rate_of_change(self) -> None:
        """Momentum reflects the direction and magnitude of change."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
            )
        )

        engine.update_tension("test", delta=0.3)

        state = engine.get_contradiction("test")
        assert state is not None
        assert state.momentum == 0.3  # Positive = intensifying


class TestPhaseTransitions:
    """Tests for rupture and resolution when tension reaches limits."""

    def test_rupture_when_tension_reaches_one(self) -> None:
        """When tension hits 1.0, a rupture event is triggered."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test Crisis",
                thesis="A",
                antithesis="B",
                tension=0.9,
            )
        )

        outcome = engine.update_tension("test", delta=0.2)

        assert outcome is not None
        assert outcome.resolution_type == "rupture"
        assert outcome.contradiction_id == "test"

        # Contradiction should be marked resolved
        state = engine.get_contradiction("test")
        assert state is not None
        assert state.resolved is True

    def test_synthesis_when_tension_reaches_zero(self) -> None:
        """When tension drops to 0.0 from above, synthesis occurs."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Resolving Conflict",
                thesis="A",
                antithesis="B",
                tension=0.3,
            )
        )

        outcome = engine.update_tension("test", delta=-0.4)

        assert outcome is not None
        assert outcome.resolution_type == "synthesis"

    def test_no_outcome_for_normal_updates(self) -> None:
        """Normal tension changes don't trigger phase transitions."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                tension=0.5,
            )
        )

        outcome = engine.update_tension("test", delta=0.1)

        assert outcome is None  # No phase transition

    def test_resolved_contradictions_cannot_be_updated(self) -> None:
        """Once resolved, a contradiction's tension cannot change."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
                tension=0.9,
            )
        )

        # Trigger resolution
        engine.update_tension("test", delta=0.2)

        # Try to update resolved contradiction
        outcome = engine.update_tension("test", delta=0.1)
        assert outcome is None  # No effect


class TestPrincipalContradiction:
    """Tests for the principal contradiction of the current period."""

    def test_set_principal_contradiction(self) -> None:
        """One contradiction can be marked as principal."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="secondary",
                name="Secondary",
                thesis="A",
                antithesis="B",
            )
        )
        engine.register_contradiction(
            ContradictionState(
                id="principal",
                name="Principal",
                thesis="X",
                antithesis="Y",
                is_principal=True,
            )
        )

        principal = engine.get_principal_contradiction()
        assert principal is not None
        assert principal.id == "principal"

    def test_no_principal_returns_none(self) -> None:
        """If no contradiction is marked principal, return None."""
        engine = ContradictionAnalysis()
        engine.register_contradiction(
            ContradictionState(
                id="test",
                name="Test",
                thesis="A",
                antithesis="B",
            )
        )

        assert engine.get_principal_contradiction() is None


class TestTwoObjectInteraction:
    """Tests for the minimal viable dialectic: two objects in contradiction.

    This is the core game loop: two agents with opposing interests
    generate tension until one yields or rupture occurs.
    """

    def test_dependency_propagation(self) -> None:
        """Changes in one contradiction affect dependent contradictions."""
        engine = ContradictionAnalysis()

        # Register two contradictions
        engine.register_contradiction(
            ContradictionState(
                id="primary",
                name="Primary Conflict",
                thesis="A",
                antithesis="B",
                tension=0.5,
            )
        )
        engine.register_contradiction(
            ContradictionState(
                id="secondary",
                name="Secondary Conflict",
                thesis="X",
                antithesis="Y",
                tension=0.3,
            )
        )

        # Establish dependency: primary affects secondary
        engine.add_dependency("primary", "secondary")

        # Update primary - should propagate to secondary
        engine.update_tension("primary", delta=0.2)

        secondary = engine.get_contradiction("secondary")
        assert secondary is not None
        # Secondary should have increased (propagation factor * delta)
        assert secondary.tension > 0.3

    def test_bidirectional_dependencies(self) -> None:
        """Contradictions can have mutual dependencies (feedback loops)."""
        engine = ContradictionAnalysis()

        engine.register_contradiction(
            ContradictionState(
                id="labor",
                name="Labor Power",
                thesis="Workers",
                antithesis="Capital",
                tension=0.4,
            )
        )
        engine.register_contradiction(
            ContradictionState(
                id="wages",
                name="Wage Struggle",
                thesis="Higher Wages",
                antithesis="Lower Wages",
                tension=0.3,
            )
        )

        # Bidirectional
        engine.add_dependency("labor", "wages")
        engine.add_dependency("wages", "labor")

        # Store initial tension VALUES (not references)
        initial_wages_tension = 0.3

        # Update labor
        engine.update_tension("labor", delta=0.1)

        # Wages should have changed via propagation
        updated_wages = engine.get_contradiction("wages")
        assert updated_wages is not None
        assert updated_wages.tension > initial_wages_tension

    def test_get_all_active_sorted_by_tension(self) -> None:
        """Active contradictions are returned sorted by tension (highest first)."""
        engine = ContradictionAnalysis()

        engine.register_contradiction(
            ContradictionState(
                id="low",
                name="Low Tension",
                thesis="A",
                antithesis="B",
                tension=0.2,
            )
        )
        engine.register_contradiction(
            ContradictionState(
                id="high",
                name="High Tension",
                thesis="X",
                antithesis="Y",
                tension=0.8,
            )
        )
        engine.register_contradiction(
            ContradictionState(
                id="mid",
                name="Mid Tension",
                thesis="M",
                antithesis="N",
                tension=0.5,
            )
        )

        active = engine.get_all_active()

        assert len(active) == 3
        assert active[0].id == "high"
        assert active[1].id == "mid"
        assert active[2].id == "low"

    def test_summary_provides_system_overview(self) -> None:
        """Summary method returns useful metrics about the system."""
        engine = ContradictionAnalysis()

        engine.register_contradiction(
            ContradictionState(
                id="a",
                name="A",
                thesis="1",
                antithesis="2",
                tension=0.6,
                is_principal=True,
            )
        )
        engine.register_contradiction(
            ContradictionState(
                id="b",
                name="B",
                thesis="3",
                antithesis="4",
                tension=0.4,
            )
        )

        summary = engine.summary()

        assert summary["total_contradictions"] == 2
        assert summary["active_contradictions"] == 2
        assert summary["principal_contradiction"] == "A"
        assert summary["highest_tension"] == 0.6
        assert summary["avg_tension"] == pytest.approx(0.5, abs=0.001)
