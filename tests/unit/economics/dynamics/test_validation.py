"""Tests for three-tier validation of transition rates and class shares.

Feature: 016-class-dynamics-engine
Task: T006
"""

from __future__ import annotations

import pytest

from babylon.economics.dynamics.types import TransitionRates
from babylon.economics.dynamics.validation import (
    validate_class_shares,
    validate_transition_rates,
)


class TestValidateTransitionRates:
    """Tests for validate_transition_rates three-tier validation."""

    def test_expected_range_returns_true_none(self) -> None:
        """Rates in expected range return (True, None)."""
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.01,
            accumulation=0.01,
            precaritization=0.02,
            stabilization=0.05,
        )
        valid, message = validate_transition_rates(rates)
        assert valid is True
        assert message is None

    def test_warning_range_returns_true_with_message(self) -> None:
        """Rates in warning range return (True, warning message)."""
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.08,  # Above expected max 0.05, within warning max 0.10
            accumulation=0.01,
            precaritization=0.02,
            stabilization=0.05,
        )
        valid, message = validate_transition_rates(rates)
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_range_returns_false_with_message(self) -> None:
        """Rates exceeding fail max return (False, error message)."""
        # Pydantic TransitionRates caps at le=1.0, so we test a rate
        # that exceeds the fail_max (0.20) but is still valid Pydantic
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.21,  # Above fail max 0.20
            accumulation=0.01,
            precaritization=0.02,
            stabilization=0.05,
        )
        valid, message = validate_transition_rates(rates)
        assert valid is False
        assert message is not None

    def test_all_rates_at_expected_lower_bound(self) -> None:
        """All rates at expected lower bounds pass."""
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.001,
            accumulation=0.001,
            precaritization=0.005,
            stabilization=0.01,
        )
        valid, message = validate_transition_rates(rates)
        assert valid is True
        assert message is None

    def test_zero_rate_triggers_warning(self) -> None:
        """Zero rate is below expected minimum, triggers warning."""
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.0,  # Below expected min 0.001
            accumulation=0.01,
            precaritization=0.02,
            stabilization=0.05,
        )
        valid, message = validate_transition_rates(rates)
        assert valid is True
        assert message is not None
        assert "WARNING" in message


class TestValidateClassShares:
    """Tests for validate_class_shares three-tier validation."""

    def test_expected_range_returns_true_none(self) -> None:
        """Shares in expected range return (True, None)."""
        valid, message = validate_class_shares(
            la_share=0.40, proletariat_share=0.35, lumpen_share=0.15
        )
        assert valid is True
        assert message is None

    def test_warning_range_returns_true_with_message(self) -> None:
        """Shares in warning range return (True, warning message)."""
        valid, message = validate_class_shares(
            la_share=0.55,  # Above expected max 0.50, within warning max 0.60
            proletariat_share=0.25,
            lumpen_share=0.10,
        )
        assert valid is True
        assert message is not None
        assert "WARNING" in message

    def test_fail_range_returns_false_with_message(self) -> None:
        """Shares in fail range return (False, error message)."""
        valid, message = validate_class_shares(
            la_share=0.40,
            proletariat_share=0.35,
            lumpen_share=-0.01,  # Negative share
        )
        assert valid is False
        assert message is not None

    def test_shares_at_expected_bounds(self) -> None:
        """Shares exactly at expected bounds pass validation."""
        valid, message = validate_class_shares(
            la_share=0.30, proletariat_share=0.25, lumpen_share=0.10
        )
        assert valid is True
        assert message is None

    @pytest.mark.parametrize(
        ("la", "prol", "lumpen"),
        [
            (0.40, 0.35, 0.15),  # Typical
            (0.30, 0.45, 0.10),  # Low LA, high prol
            (0.50, 0.25, 0.25),  # High LA, high lumpen
        ],
    )
    def test_various_expected_distributions(self, la: float, prol: float, lumpen: float) -> None:
        """Various distributions within expected ranges pass."""
        valid, message = validate_class_shares(
            la_share=la, proletariat_share=prol, lumpen_share=lumpen
        )
        assert valid is True
        assert message is None
