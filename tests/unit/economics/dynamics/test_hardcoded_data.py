"""Tests for hardcoded national dispossession data source.

Feature: 016-class-dynamics-engine
Task: T004
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.dynamics.hardcoded_data import (
    HardcodedNationalDispossessionSource,
)


class TestHardcodedNationalDispossessionSource:
    """Tests for HardcodedNationalDispossessionSource."""

    def test_foreclosure_rate_in_range(self) -> None:
        """All years 2007-2020 return foreclosure data."""
        source = HardcodedNationalDispossessionSource()
        for year in range(2007, 2021):
            rate = source.get_foreclosure_rate("00000", year)
            assert rate is not None
            assert 0.0 <= rate <= 1.0

    def test_bankruptcy_rate_in_range(self) -> None:
        """All years 2007-2020 return bankruptcy data."""
        source = HardcodedNationalDispossessionSource()
        for year in range(2007, 2021):
            rate = source.get_bankruptcy_rate("00000", year)
            assert rate is not None
            assert 0.0 <= rate <= 1.0

    def test_eviction_rate_in_range(self) -> None:
        """All years 2007-2020 return eviction data."""
        source = HardcodedNationalDispossessionSource()
        for year in range(2007, 2021):
            rate = source.get_eviction_rate("00000", year)
            assert rate is not None
            assert 0.0 <= rate <= 1.0

    def test_out_of_range_year_returns_none(self) -> None:
        """Years outside 2007-2020 return None."""
        source = HardcodedNationalDispossessionSource()
        assert source.get_foreclosure_rate("00000", 2006) is None
        assert source.get_foreclosure_rate("00000", 2021) is None
        assert source.get_bankruptcy_rate("00000", 2006) is None
        assert source.get_eviction_rate("00000", 2006) is None

    def test_crisis_year_elevated_vs_stable(self) -> None:
        """2010 crisis rates > 2015 stable rates for all sources."""
        source = HardcodedNationalDispossessionSource()
        fips = "00000"

        crisis_f = source.get_foreclosure_rate(fips, 2010)
        stable_f = source.get_foreclosure_rate(fips, 2015)
        assert crisis_f is not None and stable_f is not None
        assert crisis_f > stable_f

        crisis_b = source.get_bankruptcy_rate(fips, 2010)
        stable_b = source.get_bankruptcy_rate(fips, 2015)
        assert crisis_b is not None and stable_b is not None
        assert crisis_b > stable_b

        crisis_e = source.get_eviction_rate(fips, 2010)
        stable_e = source.get_eviction_rate(fips, 2015)
        assert crisis_e is not None and stable_e is not None
        assert crisis_e > stable_e

    def test_specific_foreclosure_values(self) -> None:
        """Spot-check specific foreclosure values from research.md."""
        source = HardcodedNationalDispossessionSource()
        fips = "00000"
        assert source.get_foreclosure_rate(fips, 2007) == pytest.approx(0.018)
        assert source.get_foreclosure_rate(fips, 2010) == pytest.approx(0.046)
        assert source.get_foreclosure_rate(fips, 2020) == pytest.approx(0.0015)

    def test_specific_bankruptcy_values(self) -> None:
        """Spot-check specific bankruptcy values from research.md."""
        source = HardcodedNationalDispossessionSource()
        fips = "00000"
        assert source.get_bankruptcy_rate(fips, 2007) == pytest.approx(0.007)
        assert source.get_bankruptcy_rate(fips, 2010) == pytest.approx(0.013)
        assert source.get_bankruptcy_rate(fips, 2020) == pytest.approx(0.004)

    def test_specific_eviction_values(self) -> None:
        """Spot-check specific eviction values from research.md."""
        source = HardcodedNationalDispossessionSource()
        fips = "00000"
        assert source.get_eviction_rate(fips, 2007) == pytest.approx(0.064)
        assert source.get_eviction_rate(fips, 2011) == pytest.approx(0.072)
        assert source.get_eviction_rate(fips, 2020) == pytest.approx(0.020)

    def test_ignores_fips_code(self) -> None:
        """National source returns same data regardless of FIPS."""
        source = HardcodedNationalDispossessionSource()
        rate_a = source.get_foreclosure_rate("26163", 2015)
        rate_b = source.get_foreclosure_rate("06037", 2015)
        assert rate_a == rate_b

    def test_protocol_compliance(self) -> None:
        """HardcodedNationalDispossessionSource satisfies DispossessionDataSource protocol."""
        from babylon.domain.economics.dynamics.data_sources import DispossessionDataSource

        source: DispossessionDataSource = HardcodedNationalDispossessionSource()
        assert source.get_foreclosure_rate("00000", 2015) is not None
