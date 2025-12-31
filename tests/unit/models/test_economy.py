"""Tests for babylon.models.entities.economy.

TDD for GlobalEconomy model - Sprint 3.4.4: Dynamic Balance.

GlobalEconomy tracks the system-wide economic state that enables
dynamic bourgeois decision-making. This is the "Gas Tank" that
forces scarcity and agency into the simulation.
"""

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

from babylon.models.entities.economy import GlobalEconomy

TC = TestConstants

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestGlobalEconomyCreation:
    """GlobalEconomy should be createable with valid data."""

    def test_default_creation(self) -> None:
        """Can create GlobalEconomy with all defaults."""
        economy = GlobalEconomy()
        assert economy.imperial_rent_pool == TC.EconomicFlow.INITIAL_RENT_POOL
        assert economy.current_super_wage_rate == TC.GlobalEconomy.DEFAULT_WAGE_RATE
        assert economy.current_repression_level == TC.Probability.MIDPOINT

    def test_custom_pool(self) -> None:
        """Can create GlobalEconomy with custom rent pool."""
        economy = GlobalEconomy(imperial_rent_pool=TC.GlobalEconomy.HEALTHY_POOL)
        assert economy.imperial_rent_pool == TC.GlobalEconomy.HEALTHY_POOL

    def test_custom_wage_rate(self) -> None:
        """Can create GlobalEconomy with custom wage rate."""
        economy = GlobalEconomy(current_super_wage_rate=TC.GlobalEconomy.HIGH_WAGE_RATE)
        assert economy.current_super_wage_rate == TC.GlobalEconomy.HIGH_WAGE_RATE

    def test_custom_repression_level(self) -> None:
        """Can create GlobalEconomy with custom repression level."""
        economy = GlobalEconomy(current_repression_level=TC.Probability.VERY_HIGH)
        assert economy.current_repression_level == TC.Probability.VERY_HIGH

    def test_full_custom_creation(self) -> None:
        """Can create GlobalEconomy with all custom values."""
        economy = GlobalEconomy(
            imperial_rent_pool=TC.GlobalEconomy.DOUBLED_POOL,
            current_super_wage_rate=TC.GlobalEconomy.LOW_WAGE_RATE,
            current_repression_level=TC.Probability.HIGH,
        )
        assert economy.imperial_rent_pool == TC.GlobalEconomy.DOUBLED_POOL
        assert economy.current_super_wage_rate == TC.GlobalEconomy.LOW_WAGE_RATE
        assert economy.current_repression_level == TC.Probability.HIGH


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestGlobalEconomyValidation:
    """GlobalEconomy should validate its fields according to type constraints."""

    def test_pool_cannot_be_negative(self) -> None:
        """imperial_rent_pool is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            GlobalEconomy(imperial_rent_pool=-10.0)

    def test_pool_can_be_zero(self) -> None:
        """imperial_rent_pool can be zero (crisis state)."""
        economy = GlobalEconomy(imperial_rent_pool=0.0)
        assert economy.imperial_rent_pool == 0.0

    def test_wage_rate_cannot_be_negative(self) -> None:
        """current_super_wage_rate is Coefficient type [0, 1]."""
        with pytest.raises(ValidationError):
            GlobalEconomy(current_super_wage_rate=-0.1)

    def test_wage_rate_cannot_exceed_one(self) -> None:
        """current_super_wage_rate is Coefficient type [0, 1]."""
        with pytest.raises(ValidationError):
            GlobalEconomy(current_super_wage_rate=1.5)

    def test_wage_rate_boundary_zero(self) -> None:
        """Wage rate can be zero (extreme austerity)."""
        economy = GlobalEconomy(current_super_wage_rate=0.0)
        assert economy.current_super_wage_rate == 0.0

    def test_wage_rate_boundary_one(self) -> None:
        """Wage rate can be 1.0 (extreme bribery)."""
        economy = GlobalEconomy(current_super_wage_rate=1.0)
        assert economy.current_super_wage_rate == 1.0

    def test_repression_cannot_be_negative(self) -> None:
        """current_repression_level is Probability type [0, 1]."""
        with pytest.raises(ValidationError):
            GlobalEconomy(current_repression_level=-0.1)

    def test_repression_cannot_exceed_one(self) -> None:
        """current_repression_level is Probability type [0, 1]."""
        with pytest.raises(ValidationError):
            GlobalEconomy(current_repression_level=1.5)

    def test_repression_boundary_values(self) -> None:
        """Repression can be 0.0 (no repression) or 1.0 (maximum repression)."""
        economy_min = GlobalEconomy(current_repression_level=0.0)
        economy_max = GlobalEconomy(current_repression_level=1.0)
        assert economy_min.current_repression_level == 0.0
        assert economy_max.current_repression_level == 1.0


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.ledger
class TestGlobalEconomyImmutability:
    """GlobalEconomy should be frozen (immutable after creation)."""

    def test_cannot_mutate_pool(self) -> None:
        """imperial_rent_pool cannot be mutated after creation."""
        economy = GlobalEconomy()
        with pytest.raises(ValidationError):
            economy.imperial_rent_pool = TC.GlobalEconomy.HALF_POOL  # type: ignore

    def test_cannot_mutate_wage_rate(self) -> None:
        """current_super_wage_rate cannot be mutated after creation."""
        economy = GlobalEconomy()
        with pytest.raises(ValidationError):
            economy.current_super_wage_rate = TC.Probability.LOW  # type: ignore

    def test_cannot_mutate_repression(self) -> None:
        """current_repression_level cannot be mutated after creation."""
        economy = GlobalEconomy()
        with pytest.raises(ValidationError):
            economy.current_repression_level = TC.Probability.EXTREME  # type: ignore


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestGlobalEconomySerialization:
    """GlobalEconomy should serialize correctly for graph storage."""

    def test_model_dump(self) -> None:
        """Can dump GlobalEconomy to dict."""
        economy = GlobalEconomy(
            imperial_rent_pool=TC.GlobalEconomy.MODERATE_POOL,
            current_super_wage_rate=TC.GlobalEconomy.MODERATE_WAGE_RATE,
            current_repression_level=TC.Probability.ELEVATED,
        )
        data = economy.model_dump()
        assert data["imperial_rent_pool"] == TC.GlobalEconomy.MODERATE_POOL
        assert data["current_super_wage_rate"] == TC.GlobalEconomy.MODERATE_WAGE_RATE
        assert data["current_repression_level"] == TC.Probability.ELEVATED

    def test_model_validate(self) -> None:
        """Can reconstruct GlobalEconomy from dict."""
        data = {
            "imperial_rent_pool": TC.GlobalEconomy.MODERATE_POOL,
            "current_super_wage_rate": TC.GlobalEconomy.MODERATE_WAGE_RATE,
            "current_repression_level": TC.Probability.ELEVATED,
        }
        economy = GlobalEconomy.model_validate(data)
        assert economy.imperial_rent_pool == TC.GlobalEconomy.MODERATE_POOL
        assert economy.current_super_wage_rate == TC.GlobalEconomy.MODERATE_WAGE_RATE
        assert economy.current_repression_level == TC.Probability.ELEVATED

    def test_json_round_trip(self) -> None:
        """GlobalEconomy survives JSON serialization round trip."""
        original = GlobalEconomy(
            imperial_rent_pool=TC.GlobalEconomy.ELEVATED_POOL,
            current_super_wage_rate=TC.GlobalEconomy.ELEVATED_WAGE_RATE,
            current_repression_level=TC.Probability.BELOW_MIDPOINT,
        )
        json_str = original.model_dump_json()
        restored = GlobalEconomy.model_validate_json(json_str)
        assert restored.imperial_rent_pool == original.imperial_rent_pool
        assert restored.current_super_wage_rate == original.current_super_wage_rate
        assert restored.current_repression_level == original.current_repression_level


# =============================================================================
# POOL RATIO HELPER TESTS
# =============================================================================


@pytest.mark.ledger
class TestGlobalEconomyPoolRatio:
    """Tests for pool ratio calculations used in decision heuristics."""

    def test_pool_ratio_calculation(self) -> None:
        """Pool ratio is pool / initial_pool."""
        # At 50% of initial pool
        economy = GlobalEconomy(imperial_rent_pool=TC.GlobalEconomy.HALF_POOL)
        ratio = economy.imperial_rent_pool / TC.EconomicFlow.INITIAL_RENT_POOL
        assert ratio == TC.Probability.MIDPOINT

    def test_pool_ratio_prosperity_threshold(self) -> None:
        """Pool ratio >= PROSPERITY_THRESHOLD indicates prosperity."""
        economy_high = GlobalEconomy(imperial_rent_pool=TC.GlobalEconomy.PROSPERITY_POOL)
        ratio = economy_high.imperial_rent_pool / TC.EconomicFlow.INITIAL_RENT_POOL
        assert ratio >= TC.GlobalEconomy.PROSPERITY_THRESHOLD  # Prosperity zone

    def test_pool_ratio_austerity_threshold(self) -> None:
        """Pool ratio < AUSTERITY_THRESHOLD indicates austerity."""
        economy_low = GlobalEconomy(imperial_rent_pool=TC.GlobalEconomy.AUSTERITY_POOL)
        ratio = economy_low.imperial_rent_pool / TC.EconomicFlow.INITIAL_RENT_POOL
        assert ratio < TC.GlobalEconomy.AUSTERITY_THRESHOLD  # Austerity zone

    def test_pool_ratio_crisis_threshold(self) -> None:
        """Pool ratio < CRISIS_THRESHOLD indicates crisis."""
        economy_crisis = GlobalEconomy(imperial_rent_pool=TC.GlobalEconomy.CRISIS_POOL)
        ratio = economy_crisis.imperial_rent_pool / TC.EconomicFlow.INITIAL_RENT_POOL
        assert ratio < TC.GlobalEconomy.CRISIS_THRESHOLD  # Crisis zone
