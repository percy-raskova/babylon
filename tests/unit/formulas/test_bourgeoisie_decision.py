"""Tests for bourgeoisie decision heuristics.

Sprint 3.4.4: Dynamic Balance - The "Driver" for the Gas Tank.

The bourgeoisie makes decisions based on:
1. Pool ratio = current_pool / initial_pool
2. Aggregate tension = avg tension across class relationships

Decision Matrix:
- pool_ratio >= 0.7 AND tension < 0.3 -> BRIBERY (increase wages)
- pool_ratio < 0.1 -> CRISIS (emergency measures)
- pool_ratio < 0.3 AND tension > 0.5 -> IRON_FIST (increase repression)
- pool_ratio < 0.3 AND tension <= 0.5 -> AUSTERITY (cut wages)
- else -> NO_CHANGE (maintain status quo)

TDD Red Phase: These tests define the contract for calculate_bourgeoisie_decision.
"""

from enum import StrEnum

import pytest
from tests.constants import TestConstants

# Import will fail initially (Red Phase)
# from babylon.systems.formulas import calculate_bourgeoisie_decision

# Alias for readability
TC = TestConstants.BourgeoisieDecision


class BourgeoisieDecision(StrEnum):
    """Possible bourgeoisie decisions based on pool and tension."""

    NO_CHANGE = "no_change"
    BRIBERY = "bribery"
    AUSTERITY = "austerity"
    IRON_FIST = "iron_fist"
    CRISIS = "crisis"


# =============================================================================
# PROSPERITY ZONE TESTS (pool_ratio >= 0.7)
# =============================================================================


@pytest.mark.math
class TestBourgeoisieDecisionProsperity:
    """When pool is healthy (>=70%), bourgeoisie can afford bribery."""

    def test_prosperity_low_tension_means_bribery(self) -> None:
        """High pool + low tension = increase wages to buy off workers.

        This is the "bread and circuses" strategy.
        """
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, wage_delta, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.8,
            aggregate_tension=0.2,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.BRIBERY
        assert wage_delta > 0  # Wages should increase
        assert repression_delta == 0  # No need for repression

    def test_prosperity_high_tension_is_no_change(self) -> None:
        """High pool + high tension = maintain status quo.

        Even with resources, high tension doesn't trigger bribery.
        """
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, wage_delta, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.8,
            aggregate_tension=0.6,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.NO_CHANGE
        assert wage_delta == 0
        assert repression_delta == 0


# =============================================================================
# AUSTERITY ZONE TESTS (pool_ratio < 0.3)
# =============================================================================


@pytest.mark.math
class TestBourgeoisieDecisionAusterity:
    """When pool is low (<30%), bourgeoisie must choose between iron fist or austerity."""

    def test_austerity_zone_low_tension_means_wage_cuts(self) -> None:
        """Low pool + low tension = cut wages (austerity).

        When workers aren't organized, bourgeoisie can extract more.
        """
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, wage_delta, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.25,
            aggregate_tension=0.3,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.AUSTERITY
        assert wage_delta < 0  # Wages should decrease
        assert repression_delta == 0  # No repression needed

    def test_austerity_zone_high_tension_means_iron_fist(self) -> None:
        """Low pool + high tension = increase repression.

        When workers are organized, bourgeoisie must use force.
        """
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, wage_delta, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.25,
            aggregate_tension=0.7,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.IRON_FIST
        assert wage_delta == 0  # Wages unchanged
        assert repression_delta > 0  # Repression increases


# =============================================================================
# CRISIS ZONE TESTS (pool_ratio < 0.1)
# =============================================================================


@pytest.mark.math
class TestBourgeoisieDecisionCrisis:
    """When pool is critical (<10%), emergency measures trigger."""

    def test_crisis_zone_triggers_emergency_measures(self) -> None:
        """Critical pool = CRISIS regardless of tension.

        The system is collapsing - both wage cuts and repression spike.
        """
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, wage_delta, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.05,
            aggregate_tension=0.3,  # Tension doesn't matter in crisis
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.CRISIS
        assert wage_delta < 0  # Wages slashed
        assert repression_delta > 0  # Repression spikes

    def test_crisis_zone_with_high_tension(self) -> None:
        """Crisis zone is crisis regardless of tension level."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, _, _ = calculate_bourgeoisie_decision(
            pool_ratio=0.08,
            aggregate_tension=0.9,  # Very high tension
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.CRISIS


# =============================================================================
# NEUTRAL ZONE TESTS (0.3 <= pool_ratio < 0.7)
# =============================================================================


@pytest.mark.math
class TestBourgeoisieDecisionNeutral:
    """When pool is in the middle zone, no drastic action needed."""

    def test_neutral_zone_is_no_change(self) -> None:
        """Mid-range pool = maintain status quo."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, wage_delta, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.5,
            aggregate_tension=0.4,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.NO_CHANGE
        assert wage_delta == 0
        assert repression_delta == 0


# =============================================================================
# BOUNDARY TESTS
# =============================================================================


@pytest.mark.math
class TestBourgeoisieDecisionBoundaries:
    """Test boundary conditions for threshold transitions."""

    def test_exactly_at_high_threshold(self) -> None:
        """Pool ratio exactly at high threshold (0.7) counts as prosperity."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, _, _ = calculate_bourgeoisie_decision(
            pool_ratio=TC.POOL_HIGH_THRESHOLD,  # Exactly at threshold
            aggregate_tension=0.2,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert decision == BourgeoisieDecision.BRIBERY

    def test_exactly_at_low_threshold(self) -> None:
        """Pool ratio exactly at low threshold (0.3) counts as neutral."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, _, _ = calculate_bourgeoisie_decision(
            pool_ratio=TC.POOL_LOW_THRESHOLD,  # Exactly at threshold
            aggregate_tension=0.4,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        # At 0.3, not < 0.3, so it's in neutral zone
        assert decision == BourgeoisieDecision.NO_CHANGE

    def test_exactly_at_critical_threshold(self) -> None:
        """Pool ratio exactly at critical threshold (0.1) counts as austerity."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        decision, _, _ = calculate_bourgeoisie_decision(
            pool_ratio=TC.POOL_CRITICAL_THRESHOLD,  # Exactly at threshold
            aggregate_tension=0.4,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        # At 0.1, not < 0.1, so it's in austerity zone (low tension)
        assert decision == BourgeoisieDecision.AUSTERITY


# =============================================================================
# DELTA MAGNITUDE TESTS
# =============================================================================


@pytest.mark.math
class TestBourgeoisieDecisionDeltaMagnitudes:
    """Test that deltas are appropriately scaled."""

    def test_bribery_wage_increase_magnitude(self) -> None:
        """Bribery wage increase should be around 5%."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        _, wage_delta, _ = calculate_bourgeoisie_decision(
            pool_ratio=0.8,
            aggregate_tension=0.2,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert 0.03 <= wage_delta <= 0.07  # ~5% +/- 2%

    def test_austerity_wage_decrease_magnitude(self) -> None:
        """Austerity wage decrease should be around 5%."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        _, wage_delta, _ = calculate_bourgeoisie_decision(
            pool_ratio=0.25,
            aggregate_tension=0.3,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert -0.07 <= wage_delta <= -0.03  # ~-5% +/- 2%

    def test_iron_fist_repression_increase_magnitude(self) -> None:
        """Iron fist repression increase should be around 10%."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        _, _, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.25,
            aggregate_tension=0.7,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert 0.08 <= repression_delta <= 0.12  # ~10% +/- 2%

    def test_crisis_has_both_deltas(self) -> None:
        """Crisis should have significant wage cut AND repression increase."""
        from babylon.systems.formulas import calculate_bourgeoisie_decision

        _, wage_delta, repression_delta = calculate_bourgeoisie_decision(
            pool_ratio=0.05,
            aggregate_tension=0.5,
            high_threshold=TC.POOL_HIGH_THRESHOLD,
            low_threshold=TC.POOL_LOW_THRESHOLD,
            critical_threshold=TC.POOL_CRITICAL_THRESHOLD,
        )

        assert wage_delta < -0.1  # At least 10% wage cut in crisis
        assert repression_delta > 0.15  # At least 15% repression spike
