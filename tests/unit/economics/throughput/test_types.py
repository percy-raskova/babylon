"""Unit tests for throughput position types.

Feature: 014-throughput-position
TDD Phase: Red/Green
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.throughput.types import ThroughputMetrics, WageShareEstimate


class TestThroughputMetrics:
    """Tests for ThroughputMetrics Pydantic model."""

    def test_valid_construction(self) -> None:
        """Construct valid ThroughputMetrics."""
        metrics = ThroughputMetrics(
            fips="26163",
            year=2022,
            tau_through=57.09,
            pi=0.878,
            supply_chain_depth=2.5,
            is_estimated=False,
            data_quality="high",
        )

        assert metrics.fips == "26163"
        assert metrics.year == 2022
        assert metrics.tau_through == pytest.approx(57.09)
        assert metrics.pi == pytest.approx(0.878)
        assert metrics.supply_chain_depth == 2.5
        assert metrics.is_estimated is False
        assert metrics.data_quality == "high"

    def test_pi_can_be_none(self) -> None:
        """pi field can be None when MELT unavailable."""
        metrics = ThroughputMetrics(
            fips="26163",
            year=2022,
            tau_through=57.09,
            pi=None,  # MELT unavailable
            supply_chain_depth=2.5,
        )

        assert metrics.pi is None

    def test_frozen_immutable(self) -> None:
        """ThroughputMetrics is immutable (frozen)."""
        metrics = ThroughputMetrics(
            fips="26163",
            year=2022,
            tau_through=57.09,
            supply_chain_depth=2.5,
        )

        with pytest.raises(ValidationError):
            metrics.tau_through = 100.0  # type: ignore[misc]

    def test_fips_validation_length(self) -> None:
        """FIPS must be exactly 5 characters."""
        with pytest.raises(ValidationError):
            ThroughputMetrics(
                fips="1234",  # Too short
                year=2022,
                tau_through=57.09,
                supply_chain_depth=2.5,
            )

        with pytest.raises(ValidationError):
            ThroughputMetrics(
                fips="123456",  # Too long
                year=2022,
                tau_through=57.09,
                supply_chain_depth=2.5,
            )

    def test_fips_validation_digits_only(self) -> None:
        """FIPS must contain only digits."""
        with pytest.raises(ValidationError):
            ThroughputMetrics(
                fips="ABCDE",
                year=2022,
                tau_through=57.09,
                supply_chain_depth=2.5,
            )

    def test_year_validation_range(self) -> None:
        """Year must be in valid range [2001, 2030]."""
        # Valid years
        ThroughputMetrics(fips="26163", year=2001, tau_through=50.0, supply_chain_depth=2.5)
        ThroughputMetrics(fips="26163", year=2030, tau_through=50.0, supply_chain_depth=2.5)

        # Invalid: too early
        with pytest.raises(ValidationError):
            ThroughputMetrics(fips="26163", year=2000, tau_through=50.0, supply_chain_depth=2.5)

        # Invalid: too late
        with pytest.raises(ValidationError):
            ThroughputMetrics(fips="26163", year=2031, tau_through=50.0, supply_chain_depth=2.5)

    def test_tau_through_must_be_positive(self) -> None:
        """τ_through must be > 0."""
        with pytest.raises(ValidationError):
            ThroughputMetrics(
                fips="26163",
                year=2022,
                tau_through=0.0,  # Invalid: not positive
                supply_chain_depth=2.5,
            )

        with pytest.raises(ValidationError):
            ThroughputMetrics(
                fips="26163",
                year=2022,
                tau_through=-10.0,  # Invalid: negative
                supply_chain_depth=2.5,
            )

    def test_supply_chain_depth_range(self) -> None:
        """Supply chain depth must be in [0.0, 5.0]."""
        # Valid bounds
        ThroughputMetrics(fips="26163", year=2022, tau_through=50.0, supply_chain_depth=0.0)
        ThroughputMetrics(fips="26163", year=2022, tau_through=50.0, supply_chain_depth=5.0)

        # Invalid: below range
        with pytest.raises(ValidationError):
            ThroughputMetrics(fips="26163", year=2022, tau_through=50.0, supply_chain_depth=-0.1)

        # Invalid: above range
        with pytest.raises(ValidationError):
            ThroughputMetrics(fips="26163", year=2022, tau_through=50.0, supply_chain_depth=5.1)

    def test_data_quality_literal(self) -> None:
        """data_quality must be one of 'high', 'medium', 'low'."""
        # Valid values
        ThroughputMetrics(
            fips="26163",
            year=2022,
            tau_through=50.0,
            supply_chain_depth=2.5,
            data_quality="high",
        )
        ThroughputMetrics(
            fips="26163",
            year=2022,
            tau_through=50.0,
            supply_chain_depth=2.5,
            data_quality="medium",
        )
        ThroughputMetrics(
            fips="26163",
            year=2022,
            tau_through=50.0,
            supply_chain_depth=2.5,
            data_quality="low",
        )

        # Invalid value
        with pytest.raises(ValidationError):
            ThroughputMetrics(
                fips="26163",
                year=2022,
                tau_through=50.0,
                supply_chain_depth=2.5,
                data_quality="unknown",  # type: ignore[arg-type]
            )


class TestWageShareEstimate:
    """Tests for WageShareEstimate Pydantic model."""

    def test_valid_construction(self) -> None:
        """Construct valid WageShareEstimate."""
        estimate = WageShareEstimate(
            fips="26163",
            naics="44",
            year=2022,
            lambda_proxy=0.08,
            confidence="high",
            avg_weekly_wage=650.0,
            employment=45000,
        )

        assert estimate.fips == "26163"
        assert estimate.naics == "44"
        assert estimate.year == 2022
        assert estimate.lambda_proxy == pytest.approx(0.08)
        assert estimate.confidence == "high"
        assert estimate.avg_weekly_wage == 650.0
        assert estimate.employment == 45000

    def test_frozen_immutable(self) -> None:
        """WageShareEstimate is immutable (frozen)."""
        estimate = WageShareEstimate(
            fips="26163",
            naics="44",
            year=2022,
            lambda_proxy=0.08,
        )

        with pytest.raises(ValidationError):
            estimate.lambda_proxy = 0.5  # type: ignore[misc]

    def test_naics_validation_length(self) -> None:
        """NAICS must be exactly 2 characters."""
        with pytest.raises(ValidationError):
            WageShareEstimate(
                fips="26163",
                naics="4",  # Too short
                year=2022,
                lambda_proxy=0.08,
            )

        with pytest.raises(ValidationError):
            WageShareEstimate(
                fips="26163",
                naics="441",  # Too long (3-digit)
                year=2022,
                lambda_proxy=0.08,
            )

    def test_lambda_proxy_must_be_non_negative(self) -> None:
        """λ_proxy must be >= 0."""
        # Zero is valid
        WageShareEstimate(fips="26163", naics="44", year=2022, lambda_proxy=0.0)

        # Negative is invalid
        with pytest.raises(ValidationError):
            WageShareEstimate(fips="26163", naics="44", year=2022, lambda_proxy=-0.1)

    def test_lambda_can_exceed_one(self) -> None:
        """λ_proxy > 1.0 is allowed (data quality issue flag)."""
        estimate = WageShareEstimate(
            fips="26163",
            naics="52",
            year=2022,
            lambda_proxy=1.5,  # Data quality issue
        )

        assert estimate.lambda_proxy == 1.5

    def test_optional_fields_default_none(self) -> None:
        """avg_weekly_wage and employment default to None."""
        estimate = WageShareEstimate(fips="26163", naics="44", year=2022, lambda_proxy=0.08)

        assert estimate.avg_weekly_wage is None
        assert estimate.employment is None

    def test_confidence_literal(self) -> None:
        """confidence must be one of 'high', 'medium', 'low'."""
        # Valid values
        WageShareEstimate(fips="26163", naics="44", year=2022, lambda_proxy=0.08, confidence="high")
        WageShareEstimate(
            fips="26163", naics="44", year=2022, lambda_proxy=0.08, confidence="medium"
        )
        WageShareEstimate(fips="26163", naics="44", year=2022, lambda_proxy=0.08, confidence="low")

        # Invalid value
        with pytest.raises(ValidationError):
            WageShareEstimate(
                fips="26163",
                naics="44",
                year=2022,
                lambda_proxy=0.08,
                confidence="unknown",  # type: ignore[arg-type]
            )
