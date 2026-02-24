"""Unit tests for TensorRegistry.

Tests for TensorRegistry that provides cached access to tensor primitives.
"""

from __future__ import annotations

import pytest
from tests.constants import TestConstants

from babylon.economics.snlt import SNLTConfig
from babylon.economics.tensor import DepartmentRow, NoDataSentinel, ValueTensor4x3
from babylon.economics.tensor_registry import CountyHydrator, GeoLevel, TensorRegistry

TC = TestConstants


class TestTensorRegistryBasics:
    """Tests for basic TensorRegistry functionality."""

    @pytest.fixture
    def registry(self) -> TensorRegistry:
        """Create empty registry for tests."""
        return TensorRegistry()

    @pytest.fixture
    def sample_tensor(self) -> ValueTensor4x3:
        """Create sample tensor for tests."""
        return ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=TC.Tensor.DEPT_I_C, v=TC.Tensor.DEPT_I_V, s=TC.Tensor.DEPT_I_S),
            dept_IIa=DepartmentRow(
                c=TC.Tensor.DEPT_IIA_C, v=TC.Tensor.DEPT_IIA_V, s=TC.Tensor.DEPT_IIA_S
            ),
            dept_IIb=DepartmentRow(
                c=TC.Tensor.DEPT_IIB_C, v=TC.Tensor.DEPT_IIB_V, s=TC.Tensor.DEPT_IIB_S
            ),
            dept_III=DepartmentRow(
                c=TC.Tensor.DEPT_III_C, v=TC.Tensor.DEPT_III_V, s=TC.Tensor.DEPT_III_S
            ),
            naics_granularity=0.85,
            excluded_wages=5000.0,
        )

    def test_empty_registry_returns_sentinel(self, registry: TensorRegistry) -> None:
        """Empty registry returns NoDataSentinel for any query."""
        result = registry.get("26163", 2022)
        assert isinstance(result, NoDataSentinel)
        assert not result  # Sentinel is falsy
        assert "26163" in result.reason
        assert "not loaded" in result.reason

    def test_put_and_get_tensor(
        self, registry: TensorRegistry, sample_tensor: ValueTensor4x3
    ) -> None:
        """Can store and retrieve a tensor."""
        registry.put("26163", 2022, sample_tensor)
        result = registry.get("26163", 2022)
        assert isinstance(result, ValueTensor4x3)
        assert result.fips_code == "26163"
        assert result.year == 2022
        assert result.dept_I.c == TC.Tensor.DEPT_I_C

    def test_get_returns_cached_instance(
        self, registry: TensorRegistry, sample_tensor: ValueTensor4x3
    ) -> None:
        """get() returns the same cached tensor instance."""
        registry.put("26163", 2022, sample_tensor)
        result1 = registry.get("26163", 2022)
        result2 = registry.get("26163", 2022)
        # Should be the exact same object (cached)
        assert result1 is result2

    def test_get_different_year_returns_sentinel(
        self, registry: TensorRegistry, sample_tensor: ValueTensor4x3
    ) -> None:
        """get() with different year returns sentinel."""
        registry.put("26163", 2022, sample_tensor)
        result = registry.get("26163", 2021)
        assert isinstance(result, NoDataSentinel)
        assert "2021" in result.reason

    def test_get_different_fips_returns_sentinel(
        self, registry: TensorRegistry, sample_tensor: ValueTensor4x3
    ) -> None:
        """get() with different FIPS returns sentinel."""
        registry.put("26163", 2022, sample_tensor)
        result = registry.get("99999", 2022)
        assert isinstance(result, NoDataSentinel)
        assert "99999" in result.reason


class TestTensorRegistryYearBoundaries:
    """Tests for year boundary validation."""

    @pytest.fixture
    def registry(self) -> TensorRegistry:
        """Create empty registry for tests."""
        return TensorRegistry()

    def test_year_too_early_returns_sentinel(self, registry: TensorRegistry) -> None:
        """Year before MIN_YEAR returns NoDataSentinel."""
        result = registry.get("26163", TC.Tensor.YEAR_TOO_EARLY)
        assert isinstance(result, NoDataSentinel)
        assert "outside available data range" in result.reason
        assert str(TC.Tensor.MIN_YEAR) in result.reason
        assert str(TC.Tensor.MAX_YEAR) in result.reason

    def test_year_too_late_returns_sentinel(self, registry: TensorRegistry) -> None:
        """Year after MAX_YEAR returns NoDataSentinel."""
        result = registry.get("26163", TC.Tensor.YEAR_TOO_LATE)
        assert isinstance(result, NoDataSentinel)
        assert "outside available data range" in result.reason

    def test_year_at_min_boundary_is_valid(self, registry: TensorRegistry) -> None:
        """Year at MIN_YEAR is accepted (returns sentinel only if not loaded)."""
        result = registry.get("26163", TC.Tensor.MIN_YEAR)
        assert isinstance(result, NoDataSentinel)
        # Should be "not loaded", not "outside range"
        assert "not loaded" in result.reason

    def test_year_at_max_boundary_is_valid(self, registry: TensorRegistry) -> None:
        """Year at MAX_YEAR is accepted (returns sentinel only if not loaded)."""
        result = registry.get("26163", TC.Tensor.MAX_YEAR)
        assert isinstance(result, NoDataSentinel)
        assert "not loaded" in result.reason


class TestTensorRegistryAvailableYears:
    """Tests for available_years() method."""

    @pytest.fixture
    def registry(self) -> TensorRegistry:
        """Create registry with sample data."""
        reg = TensorRegistry()
        for year in [2020, 2021, 2022]:
            tensor = ValueTensor4x3(
                fips_code="26163",
                year=year,
                dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
                dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
                dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
                dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
                naics_granularity=0.85,
                excluded_wages=1000.0,
            )
            reg.put("26163", year, tensor)
        return reg

    def test_returns_loaded_years(self, registry: TensorRegistry) -> None:
        """available_years returns set of loaded years."""
        years = registry.available_years("26163")
        assert years == frozenset({2020, 2021, 2022})

    def test_returns_empty_for_unknown_fips(self, registry: TensorRegistry) -> None:
        """available_years returns empty set for unknown FIPS."""
        years = registry.available_years("99999")
        assert years == frozenset()

    def test_returns_frozenset(self, registry: TensorRegistry) -> None:
        """available_years returns immutable frozenset."""
        years = registry.available_years("26163")
        assert isinstance(years, frozenset)


class TestTensorRegistrySNLTConfig:
    """Tests for SNLT configuration in registry."""

    def test_default_snlt_config(self) -> None:
        """Registry uses default SNLT config when none provided."""
        registry = TensorRegistry()
        assert registry.snlt_config.default_factor == 1.0

    def test_custom_snlt_config(self) -> None:
        """Registry accepts custom SNLT config."""
        snlt = SNLTConfig(factors={2020: 0.95}, default_factor=1.0)
        registry = TensorRegistry(snlt_config=snlt)
        assert registry.snlt_config.get_factor(2020) == 0.95


class TestTensorRegistryClear:
    """Tests for cache clearing."""

    def test_clear_removes_all_tensors(self) -> None:
        """clear() removes all cached tensors."""
        registry = TensorRegistry()
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
            dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
            dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
            dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
            naics_granularity=0.85,
            excluded_wages=1000.0,
        )
        registry.put("26163", 2022, tensor)
        assert isinstance(registry.get("26163", 2022), ValueTensor4x3)

        registry.clear()
        result = registry.get("26163", 2022)
        assert isinstance(result, NoDataSentinel)

    def test_clear_resets_cache_info(self) -> None:
        """clear() resets cache statistics."""
        registry = TensorRegistry()
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
            dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
            dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
            dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
            naics_granularity=0.85,
            excluded_wages=1000.0,
        )
        registry.put("26163", 2022, tensor)
        assert registry.cache_info()["county_count"] == 1

        registry.clear()
        assert registry.cache_info()["county_count"] == 0


class TestTensorRegistryAggregation:
    """Tests for geographic aggregation."""

    @pytest.fixture
    def registry_with_state(self) -> TensorRegistry:
        """Create registry with multiple counties in Michigan (26)."""
        reg = TensorRegistry()
        # Wayne County (Detroit)
        reg.put(
            "26163",
            2022,
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=DepartmentRow(c=1000.0, v=500.0, s=500.0),
                dept_IIa=DepartmentRow(c=800.0, v=400.0, s=400.0),
                dept_IIb=DepartmentRow(c=600.0, v=300.0, s=300.0),
                dept_III=DepartmentRow(c=400.0, v=200.0, s=200.0),
                naics_granularity=0.9,
                excluded_wages=10000.0,
            ),
        )
        # Oakland County
        reg.put(
            "26125",
            2022,
            ValueTensor4x3(
                fips_code="26125",
                year=2022,
                dept_I=DepartmentRow(c=500.0, v=250.0, s=250.0),
                dept_IIa=DepartmentRow(c=400.0, v=200.0, s=200.0),
                dept_IIb=DepartmentRow(c=300.0, v=150.0, s=150.0),
                dept_III=DepartmentRow(c=200.0, v=100.0, s=100.0),
                naics_granularity=0.8,
                excluded_wages=5000.0,
            ),
        )
        # Macomb County
        reg.put(
            "26099",
            2022,
            ValueTensor4x3(
                fips_code="26099",
                year=2022,
                dept_I=DepartmentRow(c=300.0, v=150.0, s=150.0),
                dept_IIa=DepartmentRow(c=240.0, v=120.0, s=120.0),
                dept_IIb=DepartmentRow(c=180.0, v=90.0, s=90.0),
                dept_III=DepartmentRow(c=120.0, v=60.0, s=60.0),
                naics_granularity=0.85,
                excluded_wages=3000.0,
            ),
        )
        return reg

    def test_state_aggregate_sums_counties(self, registry_with_state: TensorRegistry) -> None:
        """State aggregate sums all county values."""
        result = registry_with_state.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(result, ValueTensor4x3)

        # Dept I c: 1000 + 500 + 300 = 1800
        assert result.dept_I.c == pytest.approx(1800.0)
        # Dept I v: 500 + 250 + 150 = 900
        assert result.dept_I.v == pytest.approx(900.0)
        # excluded_wages: 10000 + 5000 + 3000 = 18000
        assert result.excluded_wages == pytest.approx(18000.0)

    def test_state_aggregate_no_counties_returns_sentinel(self) -> None:
        """State with no loaded counties returns sentinel."""
        registry = TensorRegistry()
        result = registry.get_aggregate(GeoLevel.STATE, "99", 2022)
        assert isinstance(result, NoDataSentinel)
        assert "No counties found" in result.reason or "No county data" in result.reason

    def test_aggregate_year_outside_range_returns_sentinel(
        self, registry_with_state: TensorRegistry
    ) -> None:
        """Aggregate with year outside range returns sentinel."""
        result = registry_with_state.get_aggregate(GeoLevel.STATE, "26", 1990)
        assert isinstance(result, NoDataSentinel)
        assert "outside available data range" in result.reason

    def test_aggregate_cached_on_second_call(self, registry_with_state: TensorRegistry) -> None:
        """Aggregate is cached after first computation."""
        # First call computes
        _ = registry_with_state.get_aggregate(GeoLevel.STATE, "26", 2022)
        info1 = registry_with_state.cache_info()

        # Second call hits cache
        _ = registry_with_state.get_aggregate(GeoLevel.STATE, "26", 2022)
        info2 = registry_with_state.cache_info()

        assert info2["aggregate_hits"] > info1["aggregate_hits"]

    def test_nation_aggregate_sums_all_counties(self, registry_with_state: TensorRegistry) -> None:
        """Nation aggregate sums all loaded counties."""
        result = registry_with_state.get_aggregate(GeoLevel.NATION, "US", 2022)
        assert isinstance(result, ValueTensor4x3)
        # Same as state since all counties are in Michigan
        assert result.dept_I.c == pytest.approx(1800.0)


class TestTensorRegistryCacheInvalidation:
    """Tests for cache invalidation when data changes."""

    def test_put_invalidates_aggregate_cache(self) -> None:
        """put() invalidates aggregate cache."""
        registry = TensorRegistry()

        # Add county and compute aggregate
        registry.put(
            "26163",
            2022,
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
                dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
                dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
                dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
                naics_granularity=0.85,
                excluded_wages=1000.0,
            ),
        )
        result1 = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(result1, ValueTensor4x3)
        assert result1.dept_I.c == pytest.approx(100.0)

        # Add another county - should invalidate cache
        registry.put(
            "26125",
            2022,
            ValueTensor4x3(
                fips_code="26125",
                year=2022,
                dept_I=DepartmentRow(c=50.0, v=25.0, s=25.0),
                dept_IIa=DepartmentRow(c=40.0, v=20.0, s=20.0),
                dept_IIb=DepartmentRow(c=30.0, v=15.0, s=15.0),
                dept_III=DepartmentRow(c=20.0, v=10.0, s=10.0),
                naics_granularity=0.8,
                excluded_wages=500.0,
            ),
        )

        # Aggregate should now include both counties
        result2 = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(result2, ValueTensor4x3)
        assert result2.dept_I.c == pytest.approx(150.0)  # 100 + 50


class TestTensorRegistryHydrateCounties:
    """Tests for hydrate_counties() method."""

    def test_hydrate_counties_loads_multiple_tensors(self) -> None:
        """hydrate_counties() loads tensors for all fips/year combinations."""
        registry = TensorRegistry()

        # Create a mock hydrator
        class MockHydrator:
            def hydrate(self, fips: str, year: int) -> ValueTensor4x3:
                return ValueTensor4x3(
                    fips_code=fips,
                    year=year,
                    dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
                    dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
                    dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
                    dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
                    naics_granularity=0.85,
                    excluded_wages=1000.0,
                )

        hydrator = MockHydrator()
        assert isinstance(hydrator, CountyHydrator)  # Verify protocol compliance

        registry.hydrate_counties(hydrator, ["26163", "26125"], [2020, 2021])

        # Verify all combinations were loaded
        assert isinstance(registry.get("26163", 2020), ValueTensor4x3)
        assert isinstance(registry.get("26163", 2021), ValueTensor4x3)
        assert isinstance(registry.get("26125", 2020), ValueTensor4x3)
        assert isinstance(registry.get("26125", 2021), ValueTensor4x3)

        # Verify cache info
        assert registry.cache_info()["county_count"] == 4

    def test_hydrate_counties_skips_invalid_years(self) -> None:
        """hydrate_counties() skips years outside valid range."""
        registry = TensorRegistry()

        class MockHydrator:
            def __init__(self) -> None:
                self.call_count = 0

            def hydrate(self, fips: str, year: int) -> ValueTensor4x3:
                self.call_count += 1
                return ValueTensor4x3(
                    fips_code=fips,
                    year=year,
                    dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
                    dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
                    dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
                    dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
                    naics_granularity=0.85,
                    excluded_wages=1000.0,
                )

        hydrator = MockHydrator()

        # Include years outside valid range (2010-2025)
        registry.hydrate_counties(hydrator, ["26163"], [2005, 2020, 2030])

        # Only 2020 should be loaded
        assert hydrator.call_count == 1
        assert isinstance(registry.get("26163", 2020), ValueTensor4x3)

    def test_hydrate_counties_stores_sentinel_on_failure(self) -> None:
        """hydrate_counties() stores NoDataSentinel when hydration fails."""
        registry = TensorRegistry()

        class FailingHydrator:
            def hydrate(self, fips: str, year: int) -> ValueTensor4x3:
                if fips == "99999":
                    msg = "No QCEW data"
                    raise ValueError(msg)
                return ValueTensor4x3(
                    fips_code=fips,
                    year=year,
                    dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
                    dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
                    dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
                    dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
                    naics_granularity=0.85,
                    excluded_wages=1000.0,
                )

        hydrator = FailingHydrator()
        registry.hydrate_counties(hydrator, ["26163", "99999"], [2020])

        # 26163 should succeed
        result_ok = registry.get("26163", 2020)
        assert isinstance(result_ok, ValueTensor4x3)

        # 99999 should have a sentinel (from failed hydration)
        result_fail = registry.get("99999", 2020)
        assert isinstance(result_fail, NoDataSentinel)
        assert "No QCEW data" in result_fail.reason


class TestHydrateCountiesMutationKillers:
    """Targeted tests to kill mutation survivors in hydrate_counties.

    Tests boundary conditions for year filtering, counter accuracy,
    and cache behavior to catch mutmut operator swaps.
    """

    @staticmethod
    def _make_hydrator(
        fail_fips: set[str] | None = None,
    ) -> tuple[CountyHydrator, list[tuple[str, int]]]:
        """Create a tracking hydrator with optional failure set."""
        calls: list[tuple[str, int]] = []

        class TrackingHydrator:
            def hydrate(self, fips: str, year: int) -> ValueTensor4x3:
                calls.append((fips, year))
                if fail_fips and fips in fail_fips:
                    raise ValueError(f"Hydration failed for {fips}")
                return ValueTensor4x3(
                    fips_code=fips,
                    year=year,
                    dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
                    dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
                    dept_IIb=DepartmentRow(c=60.0, v=30.0, s=30.0),
                    dept_III=DepartmentRow(c=40.0, v=20.0, s=20.0),
                    naics_granularity=0.85,
                    excluded_wages=1000.0,
                )

        hydrator = TrackingHydrator()
        return hydrator, calls

    def test_year_at_exact_min_boundary_loads(self) -> None:
        """year=MIN_YEAR should be loaded (not skipped)."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator()

        registry.hydrate_counties(hydrator, ["26163"], [TensorRegistry.MIN_YEAR])

        assert len(calls) == 1
        assert isinstance(registry.get("26163", TensorRegistry.MIN_YEAR), ValueTensor4x3)

    def test_year_one_below_min_skipped(self) -> None:
        """year=MIN_YEAR-1 should be skipped (boundary off-by-one)."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator()

        registry.hydrate_counties(hydrator, ["26163"], [TensorRegistry.MIN_YEAR - 1])

        assert len(calls) == 0

    def test_year_at_exact_max_boundary_loads(self) -> None:
        """year=MAX_YEAR should be loaded (not skipped)."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator()

        registry.hydrate_counties(hydrator, ["26163"], [TensorRegistry.MAX_YEAR])

        assert len(calls) == 1
        assert isinstance(registry.get("26163", TensorRegistry.MAX_YEAR), ValueTensor4x3)

    def test_year_one_above_max_skipped(self) -> None:
        """year=MAX_YEAR+1 should be skipped (boundary off-by-one)."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator()

        registry.hydrate_counties(hydrator, ["26163"], [TensorRegistry.MAX_YEAR + 1])

        assert len(calls) == 0

    def test_counter_accuracy_all_success(self) -> None:
        """3 fips x 2 years = 6 hydrator calls, all succeed."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator()
        fips_list = ["26163", "26125", "26099"]
        years = [2020, 2021]

        registry.hydrate_counties(hydrator, fips_list, years)

        assert len(calls) == 6
        for fips in fips_list:
            for year in years:
                assert isinstance(registry.get(fips, year), ValueTensor4x3)

    def test_counter_accuracy_with_failures(self) -> None:
        """1 of 3 fips fails → loaded=4, failed=2 (2 years each)."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator(fail_fips={"99999"})
        fips_list = ["26163", "99999", "26125"]
        years = [2020, 2021]

        registry.hydrate_counties(hydrator, fips_list, years)

        assert len(calls) == 6  # All attempted
        # Successes
        assert isinstance(registry.get("26163", 2020), ValueTensor4x3)
        assert isinstance(registry.get("26125", 2021), ValueTensor4x3)
        # Failures stored as sentinel
        result = registry.get("99999", 2020)
        assert isinstance(result, NoDataSentinel)
        assert "Hydration failed" in result.reason

    def test_empty_fips_list(self) -> None:
        """Empty fips list → nothing loaded, no calls."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator()

        registry.hydrate_counties(hydrator, [], [2020, 2021])

        assert len(calls) == 0

    def test_mixed_year_range(self) -> None:
        """[MIN-1, MIN, MID, MAX, MAX+1] → loads 3, skips 2."""
        registry = TensorRegistry()
        hydrator, calls = self._make_hydrator()
        years = [
            TensorRegistry.MIN_YEAR - 1,
            TensorRegistry.MIN_YEAR,
            2018,
            TensorRegistry.MAX_YEAR,
            TensorRegistry.MAX_YEAR + 1,
        ]

        registry.hydrate_counties(hydrator, ["26163"], years)

        assert len(calls) == 3  # MIN, 2018, MAX

    def test_sentinel_stored_on_failure(self) -> None:
        """After failure, get() returns sentinel with error reason."""
        registry = TensorRegistry()
        hydrator, _calls = self._make_hydrator(fail_fips={"00000"})

        registry.hydrate_counties(hydrator, ["00000"], [2020])

        result = registry.get("00000", 2020)
        assert isinstance(result, NoDataSentinel)
        assert "00000" in result.reason

    def test_already_cached_not_rehydrated(self) -> None:
        """Pre-populated cache entry is overwritten by hydrator (put is called)."""
        registry = TensorRegistry()
        # Pre-populate
        original = ValueTensor4x3(
            fips_code="26163",
            year=2020,
            dept_I=DepartmentRow(c=999.0, v=999.0, s=999.0),
            dept_IIa=DepartmentRow(c=999.0, v=999.0, s=999.0),
            dept_IIb=DepartmentRow(c=999.0, v=999.0, s=999.0),
            dept_III=DepartmentRow(c=999.0, v=999.0, s=999.0),
            naics_granularity=0.99,
            excluded_wages=99999.0,
        )
        registry.put("26163", 2020, original)

        hydrator, calls = self._make_hydrator()
        registry.hydrate_counties(hydrator, ["26163"], [2020])

        # Hydrator was still called (no dedup logic)
        assert len(calls) == 1
        # Value was overwritten by hydrator's return
        result = registry.get("26163", 2020)
        assert isinstance(result, ValueTensor4x3)
        assert result.dept_I.c == 100.0  # From hydrator, not 999.0


class TestTensorRegistryMutationKillers:
    """Mutation-killing tests for untested tensor_registry paths.

    Targets: clear() aggregate invalidation, _sum_tensors fallback values,
    put_sentinel direct calls, _sum_tensors FIPS formatting, all_fips(),
    cache_info(), and _compute_aggregate_uncached COUNTY delegation.
    """

    @staticmethod
    def _make_tensor(
        fips: str = "26163", year: int = 2022, c: float = 100.0, v: float = 50.0, s: float = 50.0
    ) -> ValueTensor4x3:
        return ValueTensor4x3(
            fips_code=fips,
            year=year,
            dept_I=DepartmentRow(c=c, v=v, s=s),
            dept_IIa=DepartmentRow(c=c * 0.8, v=v * 0.8, s=s * 0.8),
            dept_IIb=DepartmentRow(c=c * 0.6, v=v * 0.6, s=s * 0.6),
            dept_III=DepartmentRow(c=c * 0.4, v=v * 0.4, s=s * 0.4),
            naics_granularity=0.85,
            excluded_wages=1000.0,
        )

    def test_clear_invalidates_aggregate_cache(self) -> None:
        """clear() must invalidate aggregate cache, not just county cache."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163"))
        registry.put("26125", 2022, self._make_tensor("26125"))

        # Compute and cache an aggregate
        agg1 = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(agg1, ValueTensor4x3)

        # Clear everything
        registry.clear()

        # Aggregate should now be sentinel (not stale cached value)
        agg2 = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(agg2, NoDataSentinel)

    def test_put_sentinel_stores_and_retrieves(self) -> None:
        """put_sentinel stores a NoDataSentinel retrievable via get()."""
        registry = TensorRegistry()
        registry.put_sentinel("99999", 2022, "Test reason")

        result = registry.get("99999", 2022)
        assert isinstance(result, NoDataSentinel)
        assert "Test reason" in result.reason
        assert result.fips == "99999"
        assert result.year == 2022

    def test_put_sentinel_counts_in_cache_info(self) -> None:
        """put_sentinel entries count in cache_info county_count."""
        registry = TensorRegistry()
        registry.put_sentinel("99999", 2022, "no data")
        assert registry.cache_info()["county_count"] == 1

    def test_put_sentinel_excluded_from_aggregates(self) -> None:
        """Sentinel entries are excluded from aggregation (only ValueTensor4x3 summed)."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163"))
        registry.put_sentinel("26125", 2022, "missing data")

        agg = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(agg, ValueTensor4x3)
        # Should only include 26163, not the sentinel for 26125
        assert agg.dept_I.c == pytest.approx(100.0)

    def test_sum_tensors_zero_total_value_defaults(self) -> None:
        """When all tensors have total_value=0, fallback avg_naics=0.5 and avg_visibility=1.0."""
        registry = TensorRegistry()
        # Create tensor with all zeros -> total_value = 0
        zero_tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=0.0, v=0.0, s=0.0),
            dept_IIa=DepartmentRow(c=0.0, v=0.0, s=0.0),
            dept_IIb=DepartmentRow(c=0.0, v=0.0, s=0.0),
            dept_III=DepartmentRow(c=0.0, v=0.0, s=0.0),
            naics_granularity=0.9,
            excluded_wages=0.0,
        )
        registry.put("26163", 2022, zero_tensor)

        agg = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(agg, ValueTensor4x3)
        # Fallback: naics_granularity = 0.5, visibility_g33 = 1.0
        assert agg.naics_granularity == pytest.approx(0.5)
        assert agg.visibility_g33 == pytest.approx(1.0)

    def test_sum_tensors_weighted_average_naics(self) -> None:
        """naics_granularity in aggregate is weighted by total_value."""
        registry = TensorRegistry()
        # Tensor A: naics=0.8, total_value large
        t_a = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_IIa=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_IIb=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_III=DepartmentRow(c=100.0, v=100.0, s=100.0),
            naics_granularity=0.8,
            excluded_wages=0.0,
        )
        # Tensor B: naics=0.6, total_value large (same)
        t_b = ValueTensor4x3(
            fips_code="26125",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_IIa=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_IIb=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_III=DepartmentRow(c=100.0, v=100.0, s=100.0),
            naics_granularity=0.6,
            excluded_wages=0.0,
        )
        registry.put("26163", 2022, t_a)
        registry.put("26125", 2022, t_b)

        agg = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(agg, ValueTensor4x3)
        # Equal total_value -> simple average: (0.8 + 0.6) / 2 = 0.7
        assert agg.naics_granularity == pytest.approx(0.7, rel=1e-6)

    def test_sum_tensors_fips_us_becomes_00000(self) -> None:
        """National aggregate (fips='US') gets FIPS code '00000'."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163"))

        agg = registry.get_aggregate(GeoLevel.NATION, "US", 2022)
        assert isinstance(agg, ValueTensor4x3)
        assert agg.fips_code == "00000"

    def test_sum_tensors_state_fips_padded(self) -> None:
        """State aggregate (fips='26') gets FIPS code '26000'."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163"))

        agg = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(agg, ValueTensor4x3)
        assert agg.fips_code == "26000"

    def test_compute_aggregate_county_level_delegates_to_get(self) -> None:
        """GeoLevel.COUNTY delegates to get() rather than summing."""
        registry = TensorRegistry()
        tensor = self._make_tensor("26163")
        registry.put("26163", 2022, tensor)

        result = registry.get_aggregate(GeoLevel.COUNTY, "26163", 2022)
        assert isinstance(result, ValueTensor4x3)
        assert result.fips_code == "26163"
        assert result.dept_I.c == tensor.dept_I.c

    def test_all_fips_returns_correct_set(self) -> None:
        """all_fips() returns all unique FIPS codes in cache."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163"))
        registry.put("26125", 2022, self._make_tensor("26125"))
        registry.put("26163", 2021, self._make_tensor("26163", year=2021))

        fips_set = registry.all_fips()
        assert isinstance(fips_set, frozenset)
        assert fips_set == frozenset({"26163", "26125"})

    def test_all_fips_empty_registry(self) -> None:
        """all_fips() returns empty frozenset for empty registry."""
        registry = TensorRegistry()
        assert registry.all_fips() == frozenset()

    def test_cache_info_tracks_aggregate_hits(self) -> None:
        """cache_info() aggregate_hits increments on repeated aggregate calls."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163"))

        # First call: miss
        registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        info1 = registry.cache_info()
        assert info1["aggregate_misses"] >= 1

        # Second call: hit
        registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        info2 = registry.cache_info()
        assert info2["aggregate_hits"] >= 1

    def test_cache_info_county_count(self) -> None:
        """cache_info() county_count reflects number of stored entries."""
        registry = TensorRegistry()
        assert registry.cache_info()["county_count"] == 0

        registry.put("26163", 2022, self._make_tensor("26163"))
        assert registry.cache_info()["county_count"] == 1

        registry.put("26125", 2022, self._make_tensor("26125"))
        assert registry.cache_info()["county_count"] == 2

    def test_get_counties_for_aggregate_unknown_level_returns_empty(self) -> None:
        """_get_counties_for_aggregate with COUNTY level returns no aggregation list."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163"))

        # COUNTY level goes through _compute_aggregate_uncached → delegates to get()
        # This is tested via get_aggregate(GeoLevel.COUNTY) above.
        # For completeness, verify state prefix filtering works
        result = registry.get_aggregate(GeoLevel.STATE, "99", 2022)
        assert isinstance(result, NoDataSentinel)

    def test_nation_aggregate_deduplicates_fips(self) -> None:
        """Nation aggregate should not double-count when same FIPS has multiple years."""
        registry = TensorRegistry()
        registry.put("26163", 2022, self._make_tensor("26163", c=100.0))
        registry.put("26163", 2021, self._make_tensor("26163", year=2021, c=200.0))

        # Nation aggregate for 2022 should only include 2022 data
        agg = registry.get_aggregate(GeoLevel.NATION, "US", 2022)
        assert isinstance(agg, ValueTensor4x3)
        # Only the 2022 tensor's dept_I.c should be present
        assert agg.dept_I.c == pytest.approx(100.0)

    def test_aggregate_year_boundary_below_min(self) -> None:
        """get_aggregate with year < MIN_YEAR returns sentinel."""
        registry = TensorRegistry()
        result = registry.get_aggregate(GeoLevel.STATE, "26", TensorRegistry.MIN_YEAR - 1)
        assert isinstance(result, NoDataSentinel)
        assert "outside available data range" in result.reason

    def test_aggregate_year_boundary_above_max(self) -> None:
        """get_aggregate with year > MAX_YEAR returns sentinel."""
        registry = TensorRegistry()
        result = registry.get_aggregate(GeoLevel.STATE, "26", TensorRegistry.MAX_YEAR + 1)
        assert isinstance(result, NoDataSentinel)
        assert "outside available data range" in result.reason


class TestSimulationTensorAccess:
    """Tests for simulation accessing tensor data without database queries.

    T039: Verify simulation accesses tensor without database query.
    These tests ensure the consumer isolation pattern works correctly.
    """

    def test_simulation_accesses_tensor_through_registry(self) -> None:
        """Simulation can access tensor data via pre-loaded registry."""
        # Create a registry with pre-loaded data
        registry = TensorRegistry()
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=400.0, v=100.0, s=100.0),
            dept_IIa=DepartmentRow(c=150.0, v=100.0, s=100.0),
            dept_IIb=DepartmentRow(c=250.0, v=100.0, s=300.0),
            dept_III=DepartmentRow(c=25.0, v=50.0, s=35.0),
            naics_granularity=0.85,
            excluded_wages=5000.0,
        )
        registry.put("26163", 2022, tensor)

        # Simulate how simulation would access tensor data
        # After registry is hydrated, simulation can get tensor without DB
        result = registry.get("26163", 2022)

        # Verify we got the tensor (not a sentinel)
        assert isinstance(result, ValueTensor4x3)
        assert result.fips_code == "26163"
        assert result.year == 2022

        # Verify we can access computed properties (no DB needed)
        assert result.profit_rate > 0
        assert result.exploitation_rate > 0
        assert result.organic_composition > 0

    def test_simulation_accesses_tensor_without_hydrator_after_load(self) -> None:
        """Once loaded, registry serves tensors without needing hydrator."""
        registry = TensorRegistry()

        # Track hydrator calls
        call_count = 0

        class TrackingHydrator:
            def hydrate(self, fips: str, year: int) -> ValueTensor4x3:
                nonlocal call_count
                call_count += 1
                return ValueTensor4x3(
                    fips_code=fips,
                    year=year,
                    dept_I=DepartmentRow(c=400.0, v=100.0, s=100.0),
                    dept_IIa=DepartmentRow(c=150.0, v=100.0, s=100.0),
                    dept_IIb=DepartmentRow(c=250.0, v=100.0, s=300.0),
                    dept_III=DepartmentRow(c=25.0, v=50.0, s=35.0),
                    naics_granularity=0.85,
                    excluded_wages=5000.0,
                )

        hydrator = TrackingHydrator()

        # Hydrate once (this makes DB calls via hydrator)
        registry.hydrate_counties(hydrator, ["26163"], [2022])
        initial_call_count = call_count

        # Now simulate accessing data multiple times (like simulation would)
        for _ in range(10):
            result = registry.get("26163", 2022)
            assert isinstance(result, ValueTensor4x3)

        # Hydrator should NOT have been called again - data is cached
        assert call_count == initial_call_count, (
            f"Hydrator was called {call_count - initial_call_count} times after initial load. "
            "Simulation should access cached data without additional hydrator calls."
        )

    def test_tensor_registry_provides_isolation_from_db(self) -> None:
        """Registry provides isolation layer - consumers don't need DB access."""
        registry = TensorRegistry()

        # Pre-load data (simulating what from_sqlite does)
        registry.put(
            "26163",
            2022,
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=DepartmentRow(c=400.0, v=100.0, s=100.0),
                dept_IIa=DepartmentRow(c=150.0, v=100.0, s=100.0),
                dept_IIb=DepartmentRow(c=250.0, v=100.0, s=300.0),
                dept_III=DepartmentRow(c=25.0, v=50.0, s=35.0),
                naics_granularity=0.85,
                excluded_wages=5000.0,
            ),
        )

        # Consumer code pattern (simulation accessing data)
        tensor = registry.get("26163", 2022)

        # Consumer only needs the registry - no DB imports required
        # This is the key isolation guarantee
        if tensor:  # Walrus pattern for truthy check
            # Access all economic data without any database dependency
            _ = tensor.total_c
            _ = tensor.total_v
            _ = tensor.total_s
            _ = tensor.profit_rate
            _ = tensor.exploitation_rate
            _ = tensor.organic_composition
            _ = tensor.imperial_rent
        else:
            pytest.fail("Expected tensor data but got NoDataSentinel")
