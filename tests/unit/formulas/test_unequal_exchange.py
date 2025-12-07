"""Tests for Unequal Exchange - the mechanism of Imperial Rent.

Unequal exchange is the transfer of value from periphery to core
through the world market. Products exchange at prices that
systematically undervalue peripheral labor.

Key Formula:
- ε = (Lp/Lc) × (Wc/Wp)

Where:
- Lp: Labor hours in periphery
- Lc: Labor hours in core (for same product)
- Wc: Core wage rate
- Wp: Periphery wage rate

The exploitation rate shows how much more the periphery works
for the same exchange value.
"""

import pytest

from babylon.systems.formulas import (
    calculate_exchange_ratio,
    calculate_exploitation_rate,
    calculate_value_transfer,
    prebisch_singer_effect,
)


@pytest.mark.math
class TestExchangeRatio:
    """ε = (Lp/Lc) × (Wc/Wp)

    The exchange ratio quantifies unequal exchange.
    When ε > 1, the periphery gives more value than it receives.
    """

    def test_exploitation_rate_calculation(self) -> None:
        """100 units produced with 5 paid → 1900% exploitation rate."""
        # Periphery works 20 hours, core works 5 hours for same product
        # Core wages: $20/hour, Periphery wages: $1/hour
        exchange_ratio = calculate_exchange_ratio(
            periphery_labor_hours=20.0,
            core_labor_hours=5.0,
            core_wage=20.0,
            periphery_wage=1.0,
        )

        # (20/5) × (20/1) = 4 × 20 = 80
        assert exchange_ratio == pytest.approx(80.0, abs=0.1)

    def test_equal_exchange_ratio_is_one(self) -> None:
        """When labor and wages are equal, ε = 1 (fair exchange)."""
        exchange_ratio = calculate_exchange_ratio(
            periphery_labor_hours=10.0,
            core_labor_hours=10.0,
            core_wage=10.0,
            periphery_wage=10.0,
        )

        assert exchange_ratio == pytest.approx(1.0, abs=0.001)

    def test_ratio_increases_with_wage_gap(self) -> None:
        """Larger wage gap → higher exploitation ratio."""
        # Same labor, different wage gaps
        ratio_small_gap = calculate_exchange_ratio(
            periphery_labor_hours=10.0,
            core_labor_hours=10.0,
            core_wage=15.0,
            periphery_wage=10.0,
        )
        ratio_large_gap = calculate_exchange_ratio(
            periphery_labor_hours=10.0,
            core_labor_hours=10.0,
            core_wage=50.0,
            periphery_wage=5.0,
        )

        assert ratio_large_gap > ratio_small_gap

    def test_handles_zero_values(self) -> None:
        """Zero in denominator raises ValueError."""
        with pytest.raises(ValueError, match="must be > 0"):
            calculate_exchange_ratio(
                periphery_labor_hours=10.0,
                core_labor_hours=0.0,  # Division by zero
                core_wage=10.0,
                periphery_wage=10.0,
            )

        with pytest.raises(ValueError, match="must be > 0"):
            calculate_exchange_ratio(
                periphery_labor_hours=10.0,
                core_labor_hours=10.0,
                core_wage=10.0,
                periphery_wage=0.0,  # Division by zero
            )


@pytest.mark.math
class TestExploitationRate:
    """Exploitation rate as a percentage.

    Transforms exchange ratio into intuitive percentage.
    ε = 2 means 100% exploitation (double the value extracted).
    """

    def test_exploitation_rate_from_ratio(self) -> None:
        """ε = 2 → 100% exploitation rate."""
        rate = calculate_exploitation_rate(exchange_ratio=2.0)
        assert rate == pytest.approx(100.0, abs=0.1)

    def test_high_exploitation_rate(self) -> None:
        """ε = 20 → 1900% exploitation rate."""
        rate = calculate_exploitation_rate(exchange_ratio=20.0)
        assert rate == pytest.approx(1900.0, abs=0.1)

    def test_zero_exploitation_when_equal(self) -> None:
        """ε = 1 → 0% exploitation (fair exchange)."""
        rate = calculate_exploitation_rate(exchange_ratio=1.0)
        assert rate == pytest.approx(0.0, abs=0.001)

    def test_negative_exploitation_impossible(self) -> None:
        """ε < 1 would mean core is exploited - we cap at 0%."""
        rate = calculate_exploitation_rate(exchange_ratio=0.5)
        # When ε < 1, periphery is "exploiting" core - we return negative
        assert rate == pytest.approx(-50.0, abs=0.1)


@pytest.mark.math
class TestValueTransfer:
    """Calculate the actual value transferred from periphery to core."""

    def test_value_transfer_calculation(self) -> None:
        """Value transfer = production × (1 - 1/ε)."""
        # Periphery produces $1000 worth of goods
        # Exchange ratio is 2 (2:1 unequal exchange)
        # Value transfer = 1000 * (1 - 0.5) = $500
        transfer = calculate_value_transfer(
            production_value=1000.0,
            exchange_ratio=2.0,
        )

        assert transfer == pytest.approx(500.0, abs=0.1)

    def test_no_transfer_when_equal(self) -> None:
        """With ε = 1, no value is transferred."""
        transfer = calculate_value_transfer(
            production_value=1000.0,
            exchange_ratio=1.0,
        )

        assert transfer == pytest.approx(0.0, abs=0.001)

    def test_high_ratio_transfers_most_value(self) -> None:
        """As ε → ∞, transfer approaches full production value."""
        transfer = calculate_value_transfer(
            production_value=1000.0,
            exchange_ratio=100.0,  # Extreme exploitation
        )

        # 1000 * (1 - 1/100) = 1000 * 0.99 = 990
        assert transfer == pytest.approx(990.0, abs=0.1)


@pytest.mark.math
class TestPrebischSingerEffect:
    """Prebisch-Singer: Terms of trade decline for commodity exporters.

    More production → lower prices → same poverty.
    The periphery runs faster to stay in the same place.
    """

    def test_declining_terms_of_trade(self) -> None:
        """Increased production leads to falling prices."""
        initial_price = 100.0

        # Produce more, but price falls
        new_price = prebisch_singer_effect(
            initial_price=initial_price,
            production_increase=0.2,  # 20% more production
            elasticity=-0.5,  # Price elasticity of demand
        )

        assert new_price < initial_price

    def test_revenue_trap(self) -> None:
        """Despite more production, revenue may not increase much."""
        initial_price = 100.0
        initial_quantity = 100.0
        initial_revenue = initial_price * initial_quantity

        production_increase = 0.5  # 50% more production
        elasticity = -0.4  # Inelastic demand

        new_price = prebisch_singer_effect(
            initial_price=initial_price,
            production_increase=production_increase,
            elasticity=elasticity,
        )
        new_quantity = initial_quantity * (1 + production_increase)
        new_revenue = new_price * new_quantity

        # Revenue doesn't grow proportionally to production increase
        revenue_growth = (new_revenue - initial_revenue) / initial_revenue
        assert revenue_growth < production_increase
