"""Unit tests for VisibilityMetric adapter wrapping the gamma module.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (implementation is complete)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.types import (
    ShadowSubsidyTensor,
    VisibilityMetric,
)
from babylon.economics.tensor_hierarchy.visibility import DefaultVisibilitySource

# =============================================================================
# Helpers
# =============================================================================


def _make_gamma_iii(gamma_iii: float = 0.333, year: int = 2021) -> object:
    """Return a GammaIII-like object."""
    mock = MagicMock()
    mock.gamma_iii = gamma_iii
    mock.year = year
    return mock


def _make_shadow_subsidy(
    phi_iii_labor_hours: float = 42.0,
    phi_iii_dollars: float | None = 1_200.0,
    melt_available: bool = True,
    year: int = 2021,
) -> object:
    """Return a ShadowSubsidy-like object."""
    mock = MagicMock()
    mock.phi_iii_labor_hours = phi_iii_labor_hours
    mock.phi_iii_dollars = phi_iii_dollars
    mock.melt_available = melt_available
    mock.year = year
    return mock


def _make_gamma_calc(year: int = 2021, gamma_iii: float = 0.333) -> MagicMock:
    """Return a mock GammaIIICalculator."""
    calc = MagicMock()
    calc.compute.return_value = _make_gamma_iii(gamma_iii=gamma_iii, year=year)
    return calc


def _make_shadow_calc(
    year: int = 2021,
    labor_hours: float = 42.0,
    dollars: float | None = 1_200.0,
) -> MagicMock:
    """Return a mock ShadowSubsidyCalculator.

    compute_phi_iii(gamma_iii, melt) is called by DefaultVisibilitySource.
    """
    calc = MagicMock()
    calc.compute_phi_iii.return_value = _make_shadow_subsidy(
        phi_iii_labor_hours=labor_hours,
        phi_iii_dollars=dollars,
        melt_available=dollars is not None,
        year=year,
    )
    return calc


# =============================================================================
# DefaultVisibilitySource tests
# =============================================================================


class TestDefaultVisibilitySource:
    """Tests for DefaultVisibilitySource adapter wrapping the gamma module."""

    @pytest.fixture()
    def gamma_calc(self) -> MagicMock:
        """Mock GammaIIICalculator returning g_33=0.333 for 2021."""
        return _make_gamma_calc(year=2021, gamma_iii=0.333)

    @pytest.fixture()
    def shadow_calc(self) -> MagicMock:
        """Mock ShadowSubsidyCalculator returning phi_iii for 2021."""
        return _make_shadow_calc(year=2021, labor_hours=42.0, dollars=1_200.0)

    @pytest.fixture()
    def source(self, gamma_calc: MagicMock, shadow_calc: MagicMock) -> DefaultVisibilitySource:
        """DefaultVisibilitySource with mocked gamma dependencies."""
        return DefaultVisibilitySource(
            gamma_calculator=gamma_calc,
            shadow_calculator=shadow_calc,
        )

    def test_get_visibility_returns_metric(self, source: DefaultVisibilitySource) -> None:
        """get_visibility returns VisibilityMetric for available year."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)

    def test_get_visibility_year_preserved(self, source: DefaultVisibilitySource) -> None:
        """Returned VisibilityMetric has correct year."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)
        assert result.year == 2021

    def test_get_visibility_g33_from_gamma(self, source: DefaultVisibilitySource) -> None:
        """g_33 is set from the GammaIII.gamma_iii field."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)
        assert result.g_33 == pytest.approx(0.333, abs=1e-9)

    def test_get_visibility_g11_near_one(self, source: DefaultVisibilitySource) -> None:
        """g_11 >= 0.80 (productive dept mostly paid labor)."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)
        assert result.g_11 >= 0.80

    def test_get_visibility_g22a_near_one(self, source: DefaultVisibilitySource) -> None:
        """g_22a >= 0.80 (necessary consumption dept mostly paid)."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)
        assert result.g_22a >= 0.80

    def test_get_visibility_g22b_near_one(self, source: DefaultVisibilitySource) -> None:
        """g_22b >= 0.80 (luxury consumption dept mostly paid)."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)
        assert result.g_22b >= 0.80

    def test_get_visibility_g33_less_than_g11(self, source: DefaultVisibilitySource) -> None:
        """g_33 < g_11 (Dept III has more invisible care labor)."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)
        assert result.g_33 < result.g_11

    @pytest.mark.math
    def test_get_visibility_diagonal_consistent(self, source: DefaultVisibilitySource) -> None:
        """g_diagonal entries match individual g fields."""
        result = source.get_visibility(2021)
        assert isinstance(result, VisibilityMetric)
        diag = result.g_diagonal
        assert float(diag[0]) == pytest.approx(result.g_11, abs=1e-9)
        assert float(diag[1]) == pytest.approx(result.g_22a, abs=1e-9)
        assert float(diag[2]) == pytest.approx(result.g_22b, abs=1e-9)
        assert float(diag[3]) == pytest.approx(result.g_33, abs=1e-9)

    def test_get_visibility_sentinel_on_gamma_sentinel(self, shadow_calc: MagicMock) -> None:
        """Returns NoDataSentinel when gamma calculator returns sentinel."""
        gamma_calc = MagicMock()
        gamma_calc.compute.return_value = NoDataSentinel("national", 1800, "No ATUS data")
        source = DefaultVisibilitySource(
            gamma_calculator=gamma_calc,
            shadow_calculator=shadow_calc,
        )
        result = source.get_visibility(1800)
        assert isinstance(result, NoDataSentinel)

    def test_get_shadow_subsidy_returns_tensor(self, source: DefaultVisibilitySource) -> None:
        """get_shadow_subsidy returns ShadowSubsidyTensor for available year."""
        result = source.get_shadow_subsidy(2021)
        assert isinstance(result, ShadowSubsidyTensor)

    def test_get_shadow_subsidy_year_preserved(self, source: DefaultVisibilitySource) -> None:
        """Returned ShadowSubsidyTensor has correct year."""
        result = source.get_shadow_subsidy(2021)
        assert isinstance(result, ShadowSubsidyTensor)
        assert result.year == 2021

    def test_get_shadow_subsidy_labor_hours_from_calc(
        self, source: DefaultVisibilitySource
    ) -> None:
        """phi_iii_labor_hours comes from shadow subsidy calculator."""
        result = source.get_shadow_subsidy(2021)
        assert isinstance(result, ShadowSubsidyTensor)
        assert result.phi_iii_labor_hours == pytest.approx(42.0, abs=1e-9)

    def test_get_shadow_subsidy_dollars_from_calc(self, source: DefaultVisibilitySource) -> None:
        """phi_iii_dollars comes from shadow subsidy calculator."""
        result = source.get_shadow_subsidy(2021)
        assert isinstance(result, ShadowSubsidyTensor)
        assert result.phi_iii_dollars == pytest.approx(1_200.0, abs=1e-9)

    def test_get_shadow_subsidy_sentinel_on_gamma_sentinel(self, shadow_calc: MagicMock) -> None:
        """Returns NoDataSentinel when shadow subsidy returns sentinel."""
        gamma_calc = MagicMock()
        gamma_calc.compute.return_value = NoDataSentinel("national", 1800, "No data")
        source = DefaultVisibilitySource(
            gamma_calculator=gamma_calc,
            shadow_calculator=shadow_calc,
        )
        result = source.get_shadow_subsidy(1800)
        assert isinstance(result, NoDataSentinel)
