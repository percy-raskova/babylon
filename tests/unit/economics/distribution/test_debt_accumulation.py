"""Unit tests for DebtAccumulation model.

Feature: 024-capital-volume-iii (US1, FR-019)
TDD Red Phase: Tests define expected behavior for cumulative debt tracking.

When enterprise profit is negative (claims > surplus), debt accumulates.
When profit is positive, debt is retired (up to accumulated amount).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.distribution.types import DebtAccumulation


@pytest.mark.unit
class TestDebtAccumulationFrozen:
    """DebtAccumulation must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        debt = DebtAccumulation(
            fips_code="26163",
            year=2020,
            accumulated_debt=100.0,
            consecutive_deficit_ticks=1,
        )
        with pytest.raises(ValidationError):
            debt.accumulated_debt = 999.0  # type: ignore[misc]


@pytest.mark.unit
class TestDebtAccumulationDefault:
    """Default factory creates a zero-debt initial state."""

    def test_default_creates_zero_state(self) -> None:
        """Default factory produces zero debt and zero deficit ticks."""
        debt = DebtAccumulation.default(fips="26163", year=2020)
        assert debt.fips_code == "26163"
        assert debt.year == 2020
        assert debt.accumulated_debt == 0.0
        assert debt.consecutive_deficit_ticks == 0

    def test_default_uses_fallback_values(self) -> None:
        """Default factory uses fallback fips and year when not provided."""
        debt = DebtAccumulation.default()
        assert debt.fips_code == "00000"
        assert debt.year == 2020


@pytest.mark.unit
class TestDebtAccumulationUpdateNegativeProfit:
    """Negative profit increases debt and increments deficit ticks."""

    def test_negative_profit_increases_debt(self) -> None:
        """Debt increases by |profit| when profit < 0."""
        current = DebtAccumulation.default(fips="26163", year=2020)
        updated = DebtAccumulation.update(current, enterprise_profit=-500.0, new_year=2021)
        assert updated.accumulated_debt == pytest.approx(500.0)

    def test_negative_profit_increments_deficit_ticks(self) -> None:
        """Consecutive deficit ticks increment when profit < 0."""
        current = DebtAccumulation.default(fips="26163", year=2020)
        updated = DebtAccumulation.update(current, enterprise_profit=-500.0, new_year=2021)
        assert updated.consecutive_deficit_ticks == 1

    def test_consecutive_negative_profits_accumulate(self) -> None:
        """Multiple deficit ticks accumulate debt and increment counter."""
        state = DebtAccumulation.default(fips="26163", year=2020)
        state = DebtAccumulation.update(state, enterprise_profit=-200.0, new_year=2021)
        state = DebtAccumulation.update(state, enterprise_profit=-300.0, new_year=2022)
        assert state.accumulated_debt == pytest.approx(500.0)
        assert state.consecutive_deficit_ticks == 2


@pytest.mark.unit
class TestDebtAccumulationUpdatePositiveProfit:
    """Positive profit retires debt and resets deficit ticks."""

    def test_positive_profit_retires_debt(self) -> None:
        """Debt decreases by min(profit, accumulated_debt) when profit > 0."""
        current = DebtAccumulation(
            fips_code="26163",
            year=2020,
            accumulated_debt=1_000.0,
            consecutive_deficit_ticks=3,
        )
        updated = DebtAccumulation.update(current, enterprise_profit=400.0, new_year=2021)
        assert updated.accumulated_debt == pytest.approx(600.0)

    def test_positive_profit_resets_deficit_ticks(self) -> None:
        """Consecutive deficit ticks reset to 0 when profit >= 0."""
        current = DebtAccumulation(
            fips_code="26163",
            year=2020,
            accumulated_debt=1_000.0,
            consecutive_deficit_ticks=3,
        )
        updated = DebtAccumulation.update(current, enterprise_profit=400.0, new_year=2021)
        assert updated.consecutive_deficit_ticks == 0

    def test_debt_never_goes_below_zero(self) -> None:
        """Accumulated debt cannot become negative even with large profit."""
        current = DebtAccumulation(
            fips_code="26163",
            year=2020,
            accumulated_debt=100.0,
            consecutive_deficit_ticks=1,
        )
        updated = DebtAccumulation.update(current, enterprise_profit=5_000.0, new_year=2021)
        assert updated.accumulated_debt == pytest.approx(0.0)

    def test_zero_profit_resets_deficit_ticks(self) -> None:
        """Zero profit (profit >= 0) resets deficit ticks but does not change debt."""
        current = DebtAccumulation(
            fips_code="26163",
            year=2020,
            accumulated_debt=500.0,
            consecutive_deficit_ticks=2,
        )
        updated = DebtAccumulation.update(current, enterprise_profit=0.0, new_year=2021)
        assert updated.accumulated_debt == pytest.approx(500.0)
        assert updated.consecutive_deficit_ticks == 0

    def test_year_advances_on_update(self) -> None:
        """The updated state reflects the new year."""
        current = DebtAccumulation.default(fips="26163", year=2020)
        updated = DebtAccumulation.update(current, enterprise_profit=-100.0, new_year=2021)
        assert updated.year == 2021
        assert updated.fips_code == "26163"
