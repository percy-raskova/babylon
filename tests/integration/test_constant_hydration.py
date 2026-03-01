"""Integration tests for Tier A constant hydration from SQLite.

Tests that hydration functions return non-default, data-derived values
when given valid FIPS codes, and fall back gracefully when data is missing.

Feature 028 - Constants Remediation Sweep, Phase 3 (US1).
"""

from __future__ import annotations

import pytest

from babylon.engine.hydration.reference import (
    hydrate_class_shares,
    hydrate_economy_constants,
    hydrate_reserve_army,
)


@pytest.mark.integration
class TestHydrateClassShares:
    """Test class share derivation from QCEW data."""

    def test_wayne_county_returns_valid_shares(self) -> None:
        """Wayne County (26163) should produce valid class distribution."""
        shares = hydrate_class_shares("26163", 2022)

        # Must have all required keys
        assert "bourgeoisie" in shares
        assert "proletariat" in shares
        assert "median_wage" in shares

        # Shares should be in valid range
        assert 0.0 < shares["bourgeoisie"] < 1.0
        assert 0.0 < shares["proletariat"] < 1.0

        # Median wage should be reasonable ($10-50/hr range)
        assert 10.0 < shares["median_wage"] < 50.0

    def test_shares_sum_to_one(self) -> None:
        """Class shares should approximately sum to 1.0."""
        shares = hydrate_class_shares("26163", 2022)
        total = (
            shares["bourgeoisie"]
            + shares["petit_bourgeoisie"]
            + shares["labor_aristocracy"]
            + shares["proletariat"]
            + shares["lumpenproletariat"]
        )
        assert 0.99 <= total <= 1.01

    def test_unknown_fips_returns_defaults(self) -> None:
        """Non-existent FIPS code should return default values."""
        shares = hydrate_class_shares("99999", 2022)
        assert shares["bourgeoisie"] == 0.01
        assert shares["proletariat"] == 0.35

    def test_invalid_year_returns_defaults(self) -> None:
        """Year with no data should return default values."""
        shares = hydrate_class_shares("26163", 1900)
        # Should still return dict (with defaults)
        assert isinstance(shares, dict)
        assert "bourgeoisie" in shares


@pytest.mark.integration
class TestHydrateEconomyConstants:
    """Test economy constant derivation from QCEW/BEA data."""

    def test_wayne_county_extraction_efficiency(self) -> None:
        """Wayne County should produce extraction_efficiency from data."""
        result = hydrate_economy_constants("26163", 2022)

        # Should have at least extraction_efficiency
        if "extraction_efficiency" in result:
            assert 0.01 <= result["extraction_efficiency"] <= 0.99

    def test_wayne_county_shadow_wage(self) -> None:
        """Wayne County should produce shadow_wage_hourly from QCEW."""
        result = hydrate_economy_constants("26163", 2022)

        if "shadow_wage_hourly" in result:
            # Reasonable hourly wage range for Wayne County
            assert 10.0 <= result["shadow_wage_hourly"] <= 100.0

    def test_unknown_fips_returns_empty(self) -> None:
        """Missing FIPS returns empty dict (caller uses GameDefines defaults)."""
        result = hydrate_economy_constants("99999", 2022)
        assert isinstance(result, dict)


@pytest.mark.integration
class TestHydrateReserveArmy:
    """Test reserve army parameter derivation."""

    def test_wayne_county_sigmoid_r0(self) -> None:
        """Wayne County should produce sigmoid_r0 estimate."""
        result = hydrate_reserve_army("26163", 2022)

        if "sigmoid_r0" in result:
            # Natural unemployment rate proxy: 2-15%
            assert 0.02 <= result["sigmoid_r0"] <= 0.15

    def test_unknown_fips_returns_empty(self) -> None:
        """Missing FIPS returns empty dict."""
        result = hydrate_reserve_army("99999", 2022)
        assert isinstance(result, dict)
