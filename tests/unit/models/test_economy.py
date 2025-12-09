"""Tests for babylon.models.entities.economy.

TDD for GlobalEconomy model - Sprint 3.4.4: Dynamic Balance.

GlobalEconomy tracks the system-wide economic state that enables
dynamic bourgeois decision-making. This is the "Gas Tank" that
forces scarcity and agency into the simulation.
"""

import pytest
from pydantic import ValidationError

from babylon.models.entities.economy import GlobalEconomy

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestGlobalEconomyCreation:
    """GlobalEconomy should be createable with valid data."""

    def test_default_creation(self) -> None:
        """Can create GlobalEconomy with all defaults."""
        economy = GlobalEconomy()
        assert economy.imperial_rent_pool == 100.0
        assert economy.current_super_wage_rate == 0.20
        assert economy.current_repression_level == 0.5

    def test_custom_pool(self) -> None:
        """Can create GlobalEconomy with custom rent pool."""
        economy = GlobalEconomy(imperial_rent_pool=500.0)
        assert economy.imperial_rent_pool == 500.0

    def test_custom_wage_rate(self) -> None:
        """Can create GlobalEconomy with custom wage rate."""
        economy = GlobalEconomy(current_super_wage_rate=0.35)
        assert economy.current_super_wage_rate == 0.35

    def test_custom_repression_level(self) -> None:
        """Can create GlobalEconomy with custom repression level."""
        economy = GlobalEconomy(current_repression_level=0.8)
        assert economy.current_repression_level == 0.8

    def test_full_custom_creation(self) -> None:
        """Can create GlobalEconomy with all custom values."""
        economy = GlobalEconomy(
            imperial_rent_pool=200.0,
            current_super_wage_rate=0.15,
            current_repression_level=0.7,
        )
        assert economy.imperial_rent_pool == 200.0
        assert economy.current_super_wage_rate == 0.15
        assert economy.current_repression_level == 0.7


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
            economy.imperial_rent_pool = 50.0  # type: ignore

    def test_cannot_mutate_wage_rate(self) -> None:
        """current_super_wage_rate cannot be mutated after creation."""
        economy = GlobalEconomy()
        with pytest.raises(ValidationError):
            economy.current_super_wage_rate = 0.10  # type: ignore

    def test_cannot_mutate_repression(self) -> None:
        """current_repression_level cannot be mutated after creation."""
        economy = GlobalEconomy()
        with pytest.raises(ValidationError):
            economy.current_repression_level = 0.9  # type: ignore


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestGlobalEconomySerialization:
    """GlobalEconomy should serialize correctly for graph storage."""

    def test_model_dump(self) -> None:
        """Can dump GlobalEconomy to dict."""
        economy = GlobalEconomy(
            imperial_rent_pool=150.0,
            current_super_wage_rate=0.25,
            current_repression_level=0.6,
        )
        data = economy.model_dump()
        assert data["imperial_rent_pool"] == 150.0
        assert data["current_super_wage_rate"] == 0.25
        assert data["current_repression_level"] == 0.6

    def test_model_validate(self) -> None:
        """Can reconstruct GlobalEconomy from dict."""
        data = {
            "imperial_rent_pool": 150.0,
            "current_super_wage_rate": 0.25,
            "current_repression_level": 0.6,
        }
        economy = GlobalEconomy.model_validate(data)
        assert economy.imperial_rent_pool == 150.0
        assert economy.current_super_wage_rate == 0.25
        assert economy.current_repression_level == 0.6

    def test_json_round_trip(self) -> None:
        """GlobalEconomy survives JSON serialization round trip."""
        original = GlobalEconomy(
            imperial_rent_pool=175.0,
            current_super_wage_rate=0.30,
            current_repression_level=0.4,
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
        # At 50% of initial 100.0
        economy = GlobalEconomy(imperial_rent_pool=50.0)
        ratio = economy.imperial_rent_pool / 100.0  # Initial pool from config
        assert ratio == 0.5

    def test_pool_ratio_prosperity_threshold(self) -> None:
        """Pool ratio >= 0.7 indicates prosperity."""
        economy_high = GlobalEconomy(imperial_rent_pool=70.0)
        ratio = economy_high.imperial_rent_pool / 100.0
        assert ratio >= 0.7  # Prosperity zone

    def test_pool_ratio_austerity_threshold(self) -> None:
        """Pool ratio < 0.3 indicates austerity."""
        economy_low = GlobalEconomy(imperial_rent_pool=25.0)
        ratio = economy_low.imperial_rent_pool / 100.0
        assert ratio < 0.3  # Austerity zone

    def test_pool_ratio_crisis_threshold(self) -> None:
        """Pool ratio < 0.1 indicates crisis."""
        economy_crisis = GlobalEconomy(imperial_rent_pool=5.0)
        ratio = economy_crisis.imperial_rent_pool / 100.0
        assert ratio < 0.1  # Crisis zone
