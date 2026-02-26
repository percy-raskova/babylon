"""Fixtures for Tensor Hierarchy unit tests.

Feature: 025-tensor-hierarchy
Date: 2026-02-26
"""

from __future__ import annotations

import numpy as np
import pytest

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.protocols import (
    InterIndustryFlowSource,
    VisibilitySource,
)
from babylon.economics.tensor_hierarchy.types import (
    InterIndustryFlow,
    IOTableType,
    VisibilityMetric,
)

# =============================================================================
# Mock Data Sources
# =============================================================================


class MockInterIndustryFlowSource:
    """Mock BEA I-O flow source for testing.

    Provides configurable I-O coefficient matrices by year.
    Default: 3x3 toy economy for simple calculations.
    """

    DEFAULT_INDUSTRIES: list[str] = ["1100A1", "327C00", "33DG00"]  # toy 3-industry
    DEFAULT_YEARS: frozenset[int] = frozenset([2017, 2018, 2019, 2020, 2021])

    # Simple productive 3x3 matrix (column sums < 1.0)
    DEFAULT_MATRIX: list[list[float]] = [
        [0.10, 0.20, 0.05],
        [0.15, 0.05, 0.30],
        [0.25, 0.10, 0.08],
    ]

    def __init__(
        self,
        flows_by_year: dict[int, InterIndustryFlow] | None = None,
        industries: list[str] | None = None,
        available_years: frozenset[int] | None = None,
    ) -> None:
        """Initialize mock source.

        Args:
            flows_by_year: Optional dict of year -> InterIndustryFlow.
            industries: Optional list of industry codes.
            available_years: Optional frozenset of available years.
        """
        self._industries = industries or self.DEFAULT_INDUSTRIES
        self._available_years = (
            available_years if available_years is not None else self.DEFAULT_YEARS
        )

        if flows_by_year is not None:
            self._flows_by_year = flows_by_year
        else:
            # Build default flow for all available years
            matrix = np.array(self.DEFAULT_MATRIX, dtype=np.float64)
            self._flows_by_year = {
                year: InterIndustryFlow(
                    year=year,
                    table_type=IOTableType.USE,
                    industries=self._industries,
                    coefficients=matrix,
                )
                for year in self._available_years
            }

    def get_direct_requirements(self, year: int) -> InterIndustryFlow | NoDataSentinel:
        """Get I-O coefficient matrix for a year."""
        if year not in self._flows_by_year:
            return NoDataSentinel("national", year, f"No I-O data for year {year}")
        return self._flows_by_year[year]

    def get_industry_codes(self) -> list[str]:
        """Return ordered list of BEA industry codes."""
        return list(self._industries)

    def available_years(self) -> frozenset[int]:
        """Return available years."""
        return self._available_years


class MockVisibilitySource:
    """Mock gamma visibility source for testing.

    Provides configurable visibility metrics by year.
    Default: typical US values (g_33 ≈ 0.33, g_11/g_22a/g_22b ≈ 1.0).
    """

    DEFAULT_VISIBILITY_BY_YEAR: dict[int, VisibilityMetric] = {}  # populated below

    def __init__(self, visibility_by_year: dict[int, VisibilityMetric] | None = None) -> None:
        """Initialize with optional visibility by year.

        Args:
            visibility_by_year: Dict mapping year to VisibilityMetric.
                Pass None for defaults, pass {} for no data.
        """
        if visibility_by_year is not None:
            self._by_year = visibility_by_year
        else:
            g_diag = np.array([1.0, 1.0, 1.0, 0.333])
            self._by_year = {
                year: VisibilityMetric(
                    year=year,
                    g_diagonal=g_diag,
                    g_11=1.0,
                    g_22a=1.0,
                    g_22b=1.0,
                    g_33=0.333,
                    is_estimated=True,
                )
                for year in [2010, 2015, 2020, 2022, 2024]
            }

    def get_visibility(self, year: int) -> VisibilityMetric | NoDataSentinel:
        """Get visibility metric for a year."""
        if year not in self._by_year:
            return NoDataSentinel("national", year, f"No visibility data for year {year}")
        return self._by_year[year]

    def get_shadow_subsidy(
        self, year: int, dept_iii_value: float, melt: float | None = None
    ) -> object:
        """Stub shadow subsidy computation."""
        if year not in self._by_year:
            return NoDataSentinel("national", year, f"No visibility data for year {year}")
        metric = self._by_year[year]
        phi_hours = dept_iii_value * (1.0 - metric.g_33)
        from babylon.economics.tensor_hierarchy.types import ShadowSubsidyTensor

        return ShadowSubsidyTensor(
            year=year,
            phi_iii_labor_hours=phi_hours,
            phi_iii_dollars=phi_hours * melt if melt is not None else None,
            melt_available=melt is not None,
        )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_io_source() -> MockInterIndustryFlowSource:
    """Provide a mock I-O flow source with default 3x3 toy economy."""
    return MockInterIndustryFlowSource()


@pytest.fixture
def mock_visibility_source() -> MockVisibilitySource:
    """Provide a mock visibility source with default g_33=0.333."""
    return MockVisibilitySource()


@pytest.fixture
def sample_inter_industry_flow() -> InterIndustryFlow:
    """Provide a sample 3x3 InterIndustryFlow for 2021."""
    industries = ["1100A1", "327C00", "33DG00"]
    matrix = np.array(
        [
            [0.10, 0.20, 0.05],
            [0.15, 0.05, 0.30],
            [0.25, 0.10, 0.08],
        ],
        dtype=np.float64,
    )
    return InterIndustryFlow(
        year=2021,
        table_type=IOTableType.USE,
        industries=industries,
        coefficients=matrix,
    )


@pytest.fixture
def sample_visibility_metric() -> VisibilityMetric:
    """Provide a sample VisibilityMetric for 2022."""
    g_diag = np.array([1.0, 1.0, 1.0, 0.333])
    return VisibilityMetric(
        year=2022,
        g_diagonal=g_diag,
        g_11=1.0,
        g_22a=1.0,
        g_22b=1.0,
        g_33=0.333,
        is_estimated=True,
    )


# Ensure mock classes satisfy protocols at import time
def _check_protocol_compliance() -> None:
    """Verify mock classes satisfy their respective protocols."""
    _i: InterIndustryFlowSource = MockInterIndustryFlowSource()
    _v: VisibilitySource = MockVisibilitySource()


_check_protocol_compliance()
