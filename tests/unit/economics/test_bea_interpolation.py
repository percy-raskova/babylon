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
    """Mock SQLAlchemy session for testing."""

    def __init__(self, data: dict[tuple[str, int], tuple[float, float, float]]) -> None:
        """Initialize with test data.

        Args:
            data: Dict mapping (naics, year) to (gross_output, intermediate_inputs, compensation).
        """
        self._data = data
        self._years: dict[str, list[int]] = {}
        for naics, year in data:
            if naics not in self._years:
                self._years[naics] = []
            self._years[naics].append(year)

        for naics in self._years:
            self._years[naics].sort()

    def execute(self, query: object, params: dict[str, object]) -> MagicMock:
        """Mock execute that returns appropriate data based on query."""
        query_str = str(query)
        mock_result = MagicMock()

        if "DISTINCT dt.year" in query_str:
            # Year availability query
            naics = params["naics_code"]
            years = self._years.get(naics, [])
            mock_result.__iter__ = lambda _self, y=years: iter((yr,) for yr in y)
            return mock_result

        elif "gross_output" in query_str:
            # Ratio query
            naics = params["naics_code"]
            year = params["year"]
            if (naics, year) in self._data:
                row = self._data[(naics, year)]
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
        # gross_output=200, intermediate_inputs=100, compensation=50
        # s/v = (200 - 100 - 50) / 50 = 50/50 = 1.0
        # c/v = 100 / 50 = 2.0
        data = {("336111", 2022): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        sv_ratio = source.get_sv_ratio("336111", 2022)
        assert sv_ratio == pytest.approx(1.0)

        cv_ratio = source.get_cv_ratio("336111", 2022)
        assert cv_ratio == pytest.approx(2.0)

    def test_missing_naics_returns_none(self) -> None:
        """When NAICS code has no data, return None."""
        data = {("336111", 2022): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("999999", 2022)
        assert result is None

    def test_zero_compensation_returns_none(self) -> None:
        """When compensation is zero, return None (avoid division by zero)."""
        data = {("336111", 2022): (200.0, 100.0, 0.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result is None


class TestInterpolatingBEASourceInterpolation:
    """Test temporal interpolation behavior."""

    def test_interpolates_between_two_years(self) -> None:
        """When target year is between two available years, interpolate linearly."""
        # 2020: s/v = (200 - 100 - 50) / 50 = 1.0
        # 2024: s/v = (200 - 80 - 40) / 40 = 2.0
        # 2022 (midpoint): should be 1.5
        data = {
            ("336111", 2020): (200.0, 100.0, 50.0),
            ("336111", 2024): (200.0, 80.0, 40.0),
        }
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        # Linear interpolation: 1.0 + 0.5 * (2.0 - 1.0) = 1.5
        assert result == pytest.approx(1.5)

    def test_extrapolates_from_earlier_year(self) -> None:
        """When target year is after last available, use last available."""
        # Only have 2020 data, requesting 2023 (within max_delta=5)
        data = {("336111", 2020): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2023)
        # Should use 2020 value: s/v = 1.0
        assert result == pytest.approx(1.0)

    def test_extrapolates_from_later_year(self) -> None:
        """When target year is before first available, use first available."""
        # Only have 2022 data, requesting 2020 (within max_delta=5)
        data = {("336111", 2022): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2020)
        # Should use 2022 value: s/v = 1.0
        assert result == pytest.approx(1.0)


class TestInterpolatingBEASourceMaxDelta:
    """Test max_delta boundary behavior."""

    def test_returns_none_when_beyond_max_delta(self) -> None:
        """When no data within max_delta, return None."""
        # Have 2010 data, requesting 2022 (12 years away, > max_delta=5)
        data = {("336111", 2010): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result is None

    def test_returns_data_at_max_delta_boundary(self) -> None:
        """When data is exactly at max_delta years away, return it."""
        # Have 2017 data, requesting 2022 (5 years away, == max_delta=5)
        data = {("336111", 2017): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result == pytest.approx(1.0)

    def test_custom_max_delta(self) -> None:
        """Custom max_delta parameter is respected."""
        # Have 2010 data, requesting 2022
        data = {("336111", 2010): (200.0, 100.0, 50.0)}
        session = MockSession(data)

        # With max_delta=5, should return None
        source5 = InterpolatingBEASource(session, max_delta=5)
        assert source5.get_sv_ratio("336111", 2022) is None

        # With max_delta=15, should return data
        source15 = InterpolatingBEASource(session, max_delta=15)
        assert source15.get_sv_ratio("336111", 2022) == pytest.approx(1.0)


class TestInterpolatingBEASourceCVRatio:
    """Test c/v ratio calculation."""

    def test_cv_ratio_calculation(self) -> None:
        """c/v ratio is intermediate_inputs / compensation."""
        # c/v = 100 / 50 = 2.0
        data = {("336111", 2022): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_cv_ratio("336111", 2022)
        assert result == pytest.approx(2.0)

    def test_cv_ratio_interpolation(self) -> None:
        """c/v ratio interpolates correctly between years."""
        # 2020: c/v = 100 / 50 = 2.0
        # 2024: c/v = 200 / 50 = 4.0
        # 2022 (midpoint): should be 3.0
        data = {
            ("336111", 2020): (300.0, 100.0, 50.0),
            ("336111", 2024): (350.0, 200.0, 50.0),
        }
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_cv_ratio("336111", 2022)
        assert result == pytest.approx(3.0)


class TestInterpolatingBEASourceEdgeCases:
    """Test edge cases and error handling."""

    def test_negative_surplus_returns_zero(self) -> None:
        """When surplus is negative (loss-making), return 0.0 for s/v."""
        # gross_output=100, intermediate_inputs=80, compensation=50
        # surplus = 100 - 80 - 50 = -30 (loss)
        # s/v should be 0.0, not negative
        data = {("336111", 2022): (100.0, 80.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result == 0.0

    def test_caches_available_years(self) -> None:
        """Year availability is cached to avoid repeated queries."""
        data = {("336111", 2022): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        # First call
        source.get_sv_ratio("336111", 2022)
        # Second call should use cached years
        source.get_sv_ratio("336111", 2022)

        # Check cache was populated
        assert "336111" in source._year_cache
        assert source._year_cache["336111"] == [2022]

    def test_null_values_return_none(self) -> None:
        """When any BEA value is None/null, return None."""
        data = {("336111", 2022): (200.0, None, 50.0)}  # type: ignore[dict-item]
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        result = source.get_sv_ratio("336111", 2022)
        assert result is None


class TestInterpolatingBEASourceProtocol:
    """Test that InterpolatingBEASource satisfies BEADataSource protocol."""

    def test_satisfies_bea_data_source_protocol(self) -> None:
        """InterpolatingBEASource implements BEADataSource protocol."""
        from babylon.economics.adapters import BEADataSource

        data = {("336111", 2022): (200.0, 100.0, 50.0)}
        session = MockSession(data)
        source = InterpolatingBEASource(session, max_delta=5)

        # Runtime check
        assert isinstance(source, BEADataSource)

    def test_can_be_used_with_marxian_hydrator(self) -> None:
        """InterpolatingBEASource can be passed to MarxianHydrator."""
        from babylon.economics.hydrator import MarxianHydrator

        # This should not raise TypeError
        data = {("336111", 2022): (200.0, 100.0, 50.0)}
        session = MockSession(data)
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
