"""Unit tests for BEA ratio temporal interpolation.

Feature: 011-fundamental-tensor-primitive
Implements: T055 from tasks.md

These tests verify the InterpolatingBEASource correctly:
1. Returns exact year data when available
2. Interpolates between two available years
3. Extrapolates from nearest year within max_delta
4. Returns None when no data within max_delta
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from babylon.economics.adapters import InterpolatingBEASource

if TYPE_CHECKING:
    pass


class MockSession:
    """Mock SQLAlchemy session for testing.

    Handles three query patterns:
    1. Year query (DISTINCT dt.year + dim_industry) -> available years
    2. BEA query (gross_output_millions) -> (bea_industry_id, GO_m, II_m, VA_m)
    3. National wages query (SUM(fq.total_wages_usd)) -> total wages in dollars
    """

    def __init__(
        self,
        bea_data: dict[tuple[str, int], tuple[int, float, float, float]],
        wages_data: dict[tuple[int, int], float] | None = None,
    ) -> None:
        """Initialize with test data.

        Args:
            bea_data: Dict mapping (naics, year) to
                (bea_industry_id, gross_output_millions, intermediate_inputs_millions,
                 value_added_millions).
            wages_data: Dict mapping (bea_industry_id, year) to national wages in dollars.
                If None, defaults are computed from bea_data.
        """
        self._bea_data = bea_data
        self._wages_data: dict[tuple[int, int], float] = wages_data or {}
        self._years: dict[str, list[int]] = {}
        for naics, year in bea_data:
            if naics not in self._years:
                self._years[naics] = []
            self._years[naics].append(year)

        for naics in self._years:
            self._years[naics].sort()

    def execute(self, query: object, params: dict[str, object] | None = None) -> MagicMock:
        """Mock execute that returns appropriate data based on query."""
        query_str = str(query)
        mock_result = MagicMock()

        if "sqlite_master" in query_str:
            # Table existence check — pretend _cache table exists
            # so we skip the CREATE TABLE path in tests
            mock_result.fetchone.return_value = ("_cache_national_wages_bea",)
            return mock_result

        elif "DISTINCT dt.year" in query_str:
            # Year availability query
            params = params or {}
            naics = params["naics_code"]
            years = self._years.get(naics, [])
            mock_result.__iter__ = lambda _self, y=years: iter((yr,) for yr in y)
            return mock_result

        elif "_cache_national_wages_bea" in query_str:
            # Pre-aggregated national wages lookup
            params = params or {}
            bea_id = params["bea_industry_id"]
            year = params["year"]
            wages = self._wages_data.get((bea_id, year))
            if wages is not None:
                mock_result.fetchone.return_value = (wages,)
            else:
                mock_result.fetchone.return_value = None
            return mock_result

        elif "gross_output_millions" in query_str:
            # BEA ratio query -> (bea_industry_id, GO_m, II_m, VA_m)
            params = params or {}
            naics = params["naics_code"]
            year = params["year"]
            if (naics, year) in self._bea_data:
                row = self._bea_data[(naics, year)]
                mock_result.fetchone.return_value = row
            else:
                mock_result.fetchone.return_value = None
            return mock_result

        mock_result.fetchone.return_value = None
        mock_result.__iter__ = lambda _self: iter([])
        return mock_result


class TestInterpolatingBEASourceBasic:
    """Test basic interpolation functionality."""

    def test_exact_year_returns_direct_ratio(self) -> None:
        """When exact year data exists, return the direct ratio."""
        # BEA: bea_id=1, GO=200M, II=100M, VA=100M
        # National wages: $50M -> compensation_m = 50.0
        # s/v = (100 - 50) / 50 = 1.0
        # c/v = 100 / 50 = 2.0
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        sv_ratio = source.get_sv_ratio("336111", 2022)
        assert sv_ratio == pytest.approx(1.0)

        cv_ratio = source.get_cv_ratio("336111", 2022)
        assert cv_ratio == pytest.approx(2.0)

    def test_missing_naics_returns_none(self) -> None:
        """When NAICS code has no data, return None."""
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("999999", 2022)
        assert result is None

    def test_zero_compensation_returns_none(self) -> None:
        """When national wages are zero, return None (avoid division by zero)."""
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 0.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result is None


class TestInterpolatingBEASourceInterpolation:
    """Test temporal interpolation behavior."""

    def test_interpolates_between_two_years(self) -> None:
        """When target year is between two available years, interpolate linearly."""
        # 2020: VA=100M, wages=$50M -> s/v = (100-50)/50 = 1.0
        # 2024: VA=120M, wages=$40M -> s/v = (120-40)/40 = 2.0
        # 2022 (midpoint): should be 1.5
        bea_data = {
            ("336111", 2020): (1, 200.0, 100.0, 100.0),
            ("336111", 2024): (1, 200.0, 80.0, 120.0),
        }
        wages_data = {
            (1, 2020): 50_000_000.0,
            (1, 2024): 40_000_000.0,
        }
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        # Linear interpolation: 1.0 + 0.5 * (2.0 - 1.0) = 1.5
        assert result == pytest.approx(1.5)

    def test_extrapolates_from_earlier_year(self) -> None:
        """When target year is after last available, use last available."""
        # Only have 2020 data, requesting 2023 (within max_delta=5)
        bea_data = {("336111", 2020): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2020): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2023)
        # Should use 2020 value: s/v = 1.0
        assert result == pytest.approx(1.0)

    def test_extrapolates_from_later_year(self) -> None:
        """When target year is before first available, use first available."""
        # Only have 2022 data, requesting 2020 (within max_delta=5)
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2020)
        # Should use 2022 value: s/v = 1.0
        assert result == pytest.approx(1.0)


class TestInterpolatingBEASourceMaxDelta:
    """Test max_delta boundary behavior."""

    def test_returns_none_when_beyond_max_delta(self) -> None:
        """When no data within max_delta, return None."""
        # Have 2010 data, requesting 2022 (12 years away, > max_delta=5)
        bea_data = {("336111", 2010): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2010): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result is None

    def test_returns_data_at_max_delta_boundary(self) -> None:
        """When data is exactly at max_delta years away, return it."""
        # Have 2017 data, requesting 2022 (5 years away, == max_delta=5)
        bea_data = {("336111", 2017): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2017): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result == pytest.approx(1.0)

    def test_custom_max_delta(self) -> None:
        """Custom max_delta parameter is respected."""
        # Have 2010 data, requesting 2022
        bea_data = {("336111", 2010): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2010): 50_000_000.0}
        session = MockSession(bea_data, wages_data)

        # With max_delta=5, should return None
        source5 = InterpolatingBEASource(session, max_delta=5)
        assert source5.get_sv_ratio("336111", 2022) is None

        # With max_delta=15, should return data
        source15 = InterpolatingBEASource(session, max_delta=15)
        assert source15.get_sv_ratio("336111", 2022) == pytest.approx(1.0)


class TestInterpolatingBEASourceCVRatio:
    """Test c/v ratio calculation."""

    def test_cv_ratio_calculation(self) -> None:
        """c/v ratio is intermediate_inputs_millions / compensation_millions."""
        # II=100M, wages=$50M -> compensation_m=50, c/v = 100 / 50 = 2.0
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_cv_ratio("336111", 2022)
        assert result == pytest.approx(2.0)

    def test_cv_ratio_interpolation(self) -> None:
        """c/v ratio interpolates correctly between years."""
        # 2020: II=100M, wages=$50M -> c/v = 100/50 = 2.0
        # 2024: II=200M, wages=$50M -> c/v = 200/50 = 4.0
        # 2022 (midpoint): should be 3.0
        bea_data = {
            ("336111", 2020): (1, 300.0, 100.0, 200.0),
            ("336111", 2024): (1, 350.0, 200.0, 150.0),
        }
        wages_data = {
            (1, 2020): 50_000_000.0,
            (1, 2024): 50_000_000.0,
        }
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_cv_ratio("336111", 2022)
        assert result == pytest.approx(3.0)


class TestInterpolatingBEASourceEdgeCases:
    """Test edge cases and error handling."""

    def test_negative_surplus_returns_zero(self) -> None:
        """When surplus is negative (loss-making), return 0.0 for s/v."""
        # VA=20M, wages=$30M -> compensation_m=30
        # surplus = 20 - 30 = -10 (loss)
        # s/v should be 0.0, not negative
        bea_data = {("336111", 2022): (1, 100.0, 80.0, 20.0)}
        wages_data = {(1, 2022): 30_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result == 0.0

    def test_caches_available_years(self) -> None:
        """Year availability is cached to avoid repeated queries."""
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        # First call
        source.get_sv_ratio("336111", 2022)
        # Second call should use cached years
        source.get_sv_ratio("336111", 2022)

        # Check cache was populated
        assert "336111" in source._year_cache
        assert source._year_cache["336111"] == [2022]

    def test_caches_national_wages(self) -> None:
        """National wages are cached to avoid repeated expensive queries."""
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        # First call populates cache
        source.get_sv_ratio("336111", 2022)

        # Check wages cache was populated
        assert (1, 2022) in source._wages_cache
        assert source._wages_cache[(1, 2022)] == 50_000_000.0

    def test_null_values_return_none(self) -> None:
        """When any BEA value is None/null, return None."""
        bea_data = {("336111", 2022): (1, 200.0, None, 100.0)}  # type: ignore[dict-item]
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result is None


class TestInterpolatingBEASourceProtocol:
    """Test that InterpolatingBEASource satisfies BEADataSource protocol."""

    def test_satisfies_bea_data_source_protocol(self) -> None:
        """InterpolatingBEASource implements BEADataSource protocol."""
        from babylon.economics.adapters import BEADataSource

        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        # Runtime check
        assert isinstance(source, BEADataSource)

    def test_can_be_used_with_marxian_hydrator(self) -> None:
        """InterpolatingBEASource can be passed to MarxianHydrator."""
        from babylon.economics.hydrator import MarxianHydrator

        # This should not raise TypeError
        bea_data = {("336111", 2022): (1, 200.0, 100.0, 100.0)}
        wages_data = {(1, 2022): 50_000_000.0}
        session = MockSession(bea_data, wages_data)
        source = InterpolatingBEASource(session, max_delta=5)

        # Create mock QCEW source
        qcew_mock = MagicMock()
        qcew_mock.fetch_county_wages.return_value = []

        # Create mock dept mapper
        dept_mapper_mock = MagicMock()
        dept_mapper_mock.get_allocation.return_value = None
        dept_mapper_mock.get_default_sv_ratio.return_value = 1.0
        dept_mapper_mock.get_default_cv_ratio.return_value = 2.0

        # Should not raise - protocol is satisfied
        hydrator = MarxianHydrator(qcew_mock, source, dept_mapper_mock)
        assert hydrator is not None
