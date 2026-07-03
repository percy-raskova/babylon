"""Tests for dispossession risk calculator.

Feature: 016-class-dynamics-engine
Task: T017
"""

from __future__ import annotations

import pytest

from babylon.economics.dynamics.dispossession import DefaultDispossessionCalculator
from babylon.economics.dynamics.hardcoded_data import (
    HardcodedNationalDispossessionSource,
)
from babylon.economics.dynamics.types import DispossessionRisk
from babylon.economics.tensor import NoDataSentinel
from tests.unit.economics.dynamics.conftest import MockDispossessionDataSource


class TestDefaultDispossessionCalculator:
    """Tests for DefaultDispossessionCalculator per US2 acceptance scenarios."""

    def test_scenario1_stable_year_low_risk(self) -> None:
        """S1: Stable year (2015) -> low composite dispossession risk.

        Given stable-year rates, the composite risk is low, reflecting
        normal economic churn.
        """
        source = HardcodedNationalDispossessionSource()
        calc = DefaultDispossessionCalculator(source)
        result = calc.compute(fips="26163", year=2015)

        assert isinstance(result, DispossessionRisk)
        assert result.la_to_p_rate < 0.02  # low dispossession
        assert result.p_to_l_component < 0.05  # moderate eviction-driven
        assert result.foreclosure_available is True
        assert result.bankruptcy_available is True
        assert result.eviction_available is True

    def test_scenario2_crisis_year_elevated(self) -> None:
        """S2: Crisis year (2010) -> at least 2x stable-year baseline.

        Given 2010 crisis rates, the composite risk is significantly
        elevated compared to 2015 stable baseline.
        """
        source = HardcodedNationalDispossessionSource()
        calc = DefaultDispossessionCalculator(source)

        crisis = calc.compute(fips="26163", year=2010)
        stable = calc.compute(fips="26163", year=2015)

        assert isinstance(crisis, DispossessionRisk)
        assert isinstance(stable, DispossessionRisk)
        assert crisis.la_to_p_rate >= 2.0 * stable.la_to_p_rate

    def test_scenario3_eviction_affects_p_to_l(self) -> None:
        """S3: High eviction primarily affects proletariat-to-lumpen.

        Given a county with high eviction but low foreclosure, the
        p_to_l_component should be much larger relative to foreclosure
        contribution.
        """
        source = MockDispossessionDataSource(
            foreclosure={2015: 0.001},  # very low
            bankruptcy={2015: 0.005},
            eviction={2015: 0.10},  # very high
        )
        calc = DefaultDispossessionCalculator(source)
        result = calc.compute(fips="26163", year=2015)

        assert isinstance(result, DispossessionRisk)
        # P->L rate heavily weighted by eviction (0.6 weight)
        # la_to_p rate barely affected by eviction (0.1 weight)
        assert result.p_to_l_component > result.la_to_p_rate

    def test_scenario4_missing_data_returns_sentinel(self) -> None:
        """S4: Missing data -> NoDataSentinel with specific reason.

        Given dispossession data unavailable for a year, the system
        returns NoDataSentinel identifying which source is missing.
        """
        source = HardcodedNationalDispossessionSource()
        calc = DefaultDispossessionCalculator(source)
        result = calc.compute(fips="26163", year=2005)

        assert isinstance(result, NoDataSentinel)
        assert "foreclosure" in result.reason.lower()

    def test_missing_bankruptcy_only(self) -> None:
        """Missing only bankruptcy returns NoDataSentinel with bankruptcy reason."""
        source = MockDispossessionDataSource(
            foreclosure={2015: 0.006},
            bankruptcy={},  # no data
            eviction={2015: 0.063},
        )
        calc = DefaultDispossessionCalculator(source)
        result = calc.compute(fips="26163", year=2015)

        assert isinstance(result, NoDataSentinel)
        assert "bankruptcy" in result.reason.lower()

    def test_missing_eviction_only(self) -> None:
        """Missing only eviction returns NoDataSentinel with eviction reason."""
        source = MockDispossessionDataSource(
            foreclosure={2015: 0.006},
            bankruptcy={2015: 0.006},
            eviction={},  # no data
        )
        calc = DefaultDispossessionCalculator(source)
        result = calc.compute(fips="26163", year=2015)

        assert isinstance(result, NoDataSentinel)
        assert "eviction" in result.reason.lower()

    def test_composite_weighting_formula(self) -> None:
        """Verify composite weighting matches research.md section 3a.

        LA->P = 0.6*foreclosure + 0.3*bankruptcy + 0.1*eviction
        P->L  = 0.1*foreclosure + 0.3*bankruptcy + 0.6*eviction
        """
        f, b, e = 0.04, 0.01, 0.07
        source = MockDispossessionDataSource(
            foreclosure={2015: f},
            bankruptcy={2015: b},
            eviction={2015: e},
        )
        calc = DefaultDispossessionCalculator(source)
        result = calc.compute(fips="26163", year=2015)

        assert isinstance(result, DispossessionRisk)
        expected_la_to_p = 0.6 * f + 0.3 * b + 0.1 * e
        expected_p_to_l = 0.1 * f + 0.3 * b + 0.6 * e
        assert result.la_to_p_rate == pytest.approx(expected_la_to_p)
        assert result.p_to_l_component == pytest.approx(expected_p_to_l)

    def test_protocol_compliance(self) -> None:
        """DefaultDispossessionCalculator satisfies DispossessionCalculator protocol."""
        from babylon.economics.dynamics.data_sources import DispossessionCalculator

        source = HardcodedNationalDispossessionSource()
        calc: DispossessionCalculator = DefaultDispossessionCalculator(source)
        result = calc.compute(fips="26163", year=2015)
        assert isinstance(result, DispossessionRisk)
