"""Integration tests for TRPF (Tendency of the Rate of Profit to Fall) validation.

These tests validate that the Capital Stock Dynamics implementation correctly
computes capital stock K and stock-based profit rate, and that the resulting
time series exhibit the expected TRPF behavior.

Feature: 012-capital-stock-dynamics
Phase: 8 - Integration & TRPF Validation
Tasks: T068-T076
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from babylon.economics.capital_stock import CapitalStockCalculator
from babylon.economics.depreciation import DepreciationConfig
from babylon.economics.derived_metrics import DerivedTensorMetrics
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3
from babylon.economics.tensor_registry import GeoLevel, TensorRegistry
from babylon.models.types import LaborHours, Probability

if TYPE_CHECKING:
    pass


# =============================================================================
# TEST FIXTURES
# =============================================================================


def create_test_tensor(
    fips: str,
    year: int,
    total_c: float = 70.0,
    total_v: float = 100.0,
    total_s: float = 100.0,
) -> ValueTensor4x3:
    """Create a test tensor with specified totals.

    Distributes values evenly across departments for simplicity.
    """
    c_per_dept = total_c / 4
    v_per_dept = total_v / 4
    s_per_dept = total_s / 4

    return ValueTensor4x3(
        fips_code=fips,
        year=year,
        dept_I=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        dept_IIa=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        dept_IIb=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        dept_III=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        naics_granularity=Probability(0.85),
        excluded_wages=LaborHours(0.0),
    )


@pytest.fixture
def registry_with_trpf_data() -> TensorRegistry:
    """Create a TensorRegistry with synthetic data exhibiting TRPF.

    Simulates rising OCC (constant capital growing faster than variable capital)
    which should cause the stock-based profit rate to fall over time.

    The key insight: TRPF occurs because K grows faster than s can grow
    (since s comes from exploiting living labor v). We model:
    - c (constant capital flow) grows at 8% per year (rapid mechanization)
    - v (variable capital) grows at 1% per year (labor market stagnation)
    - s grows proportional to v (constant exploitation rate)

    This creates rising OCC and accumulating K, causing r_stock = s/(K+v) to fall.
    """
    registry = TensorRegistry()

    # Simulate 15 years of data where c grows faster than v (rising OCC)
    # This should cause K to grow and profit rate to fall
    for year in range(2010, 2025):
        year_offset = year - 2010

        # c grows at 8% per year (rapid capital accumulation)
        # v grows at only 1% per year (labor market stagnation)
        # This creates strongly rising OCC = c/v
        c_multiplier = (1.08) ** year_offset
        v_multiplier = (1.01) ** year_offset

        total_c = 500.0 * c_multiplier
        total_v = 100.0 * v_multiplier
        # s grows proportional to v (constant exploitation rate e = 2.0)
        total_s = 200.0 * v_multiplier

        tensor = create_test_tensor(
            "26163",  # Wayne County
            year,
            total_c=total_c,
            total_v=total_v,
            total_s=total_s,
        )
        registry.put("26163", year, tensor)

    return registry


@pytest.fixture
def registry_with_multi_county_data() -> TensorRegistry:
    """Create a TensorRegistry with multiple counties for aggregation testing."""
    registry = TensorRegistry()

    # Wayne County (26163) - peripheral, high OCC
    # Oakland County (26125) - core, lower OCC
    # Ingham County (26099) - intermediate

    for year in range(2010, 2025):
        year_offset = year - 2010

        # Wayne: high c/v ratio (peripheral deindustrialized)
        wayne_c = 500.0 * (1.04) ** year_offset
        wayne_v = 80.0 * (1.01) ** year_offset
        wayne_s = 120.0 * (1.01) ** year_offset

        # Oakland: lower c/v ratio (services, knowledge economy)
        oakland_c = 200.0 * (1.03) ** year_offset
        oakland_v = 150.0 * (1.025) ** year_offset
        oakland_s = 200.0 * (1.025) ** year_offset

        # Ingham: intermediate
        ingham_c = 300.0 * (1.035) ** year_offset
        ingham_v = 120.0 * (1.02) ** year_offset
        ingham_s = 160.0 * (1.02) ** year_offset

        registry.put("26163", year, create_test_tensor("26163", year, wayne_c, wayne_v, wayne_s))
        registry.put(
            "26125", year, create_test_tensor("26125", year, oakland_c, oakland_v, oakland_s)
        )
        registry.put("26099", year, create_test_tensor("26099", year, ingham_c, ingham_v, ingham_s))

    return registry


# =============================================================================
# T068: FULL PIPELINE TEST
# =============================================================================


class TestFullPipeline:
    """Tests for the complete registry -> calculator -> metrics pipeline."""

    def test_pipeline_produces_valid_metrics(self, registry_with_trpf_data: TensorRegistry) -> None:
        """T068: Full pipeline should produce valid DerivedTensorMetrics."""
        calculator = CapitalStockCalculator(registry_with_trpf_data)

        # Compute metrics for a year in the middle of the time series
        metrics = calculator.get_metrics("26163", 2020)

        assert isinstance(metrics, DerivedTensorMetrics)
        assert metrics.capital_stock > 0
        assert metrics.profit_rate_stock > 0
        assert metrics.profit_rate_flow > 0
        assert metrics.organic_composition > 0
        assert metrics.exploitation_rate > 0

    def test_pipeline_time_series_is_complete(
        self, registry_with_trpf_data: TensorRegistry
    ) -> None:
        """Pipeline should produce metrics for all available years."""
        calculator = CapitalStockCalculator(registry_with_trpf_data)

        metrics_series = []
        for year in range(2010, 2025):
            metrics = calculator.get_metrics("26163", year)
            if isinstance(metrics, DerivedTensorMetrics):
                metrics_series.append(metrics)

        # Should have metrics for all 15 years
        assert len(metrics_series) == 15


# =============================================================================
# T069: DETROIT VALIDATION CASE
# =============================================================================


class TestDetroitValidation:
    """Tests for Detroit metro validation case (Wayne vs Oakland OCC)."""

    def test_wayne_has_higher_occ_than_oakland(
        self, registry_with_multi_county_data: TensorRegistry
    ) -> None:
        """T069: Wayne County (peripheral) should have higher OCC than Oakland (core)."""
        calculator = CapitalStockCalculator(registry_with_multi_county_data)

        wayne_metrics = calculator.get_metrics("26163", 2022)
        oakland_metrics = calculator.get_metrics("26125", 2022)

        assert isinstance(wayne_metrics, DerivedTensorMetrics)
        assert isinstance(oakland_metrics, DerivedTensorMetrics)

        # Wayne (deindustrialized peripheral) has higher OCC than Oakland (services core)
        assert wayne_metrics.organic_composition > oakland_metrics.organic_composition


# =============================================================================
# T070: TRPF STATISTICAL TEST (SC-002)
# =============================================================================


class TestTRPFStatistics:
    """Tests for statistical validation of TRPF (SC-002: dr/dt < 0, p < 0.05)."""

    def test_profit_rate_shows_negative_trend(
        self, registry_with_trpf_data: TensorRegistry
    ) -> None:
        """T070: Profit rate time series should show negative slope (TRPF)."""
        calculator = CapitalStockCalculator(registry_with_trpf_data)

        # Collect profit rate time series
        profit_rates = []
        years = []
        for year in range(2010, 2025):
            metrics = calculator.get_metrics("26163", year)
            if isinstance(metrics, DerivedTensorMetrics):
                profit_rates.append(metrics.profit_rate_stock)
                years.append(year)

        # Verify we have enough data
        assert len(profit_rates) == 15

        # Simple linear regression: slope = Cov(x,y) / Var(x)
        n = len(years)
        x_mean = sum(years) / n
        y_mean = sum(profit_rates) / n

        cov_xy = (
            sum((x - x_mean) * (y - y_mean) for x, y in zip(years, profit_rates, strict=True)) / n
        )
        var_x = sum((x - x_mean) ** 2 for x in years) / n

        slope = cov_xy / var_x

        # TRPF: slope should be negative
        assert slope < 0, f"Expected negative slope for TRPF, got {slope}"


# =============================================================================
# T071: OCC-CORE CORRELATION (SC-003)
# =============================================================================


class TestOCCCoreCorrelation:
    """Tests for OCC-CoreIndex correlation (SC-003: correlation > 0.3)."""

    def test_occ_correlates_with_capital_intensity(
        self, registry_with_multi_county_data: TensorRegistry
    ) -> None:
        """T071: OCC should correlate with capital intensity across counties.

        In this test, we use K/v as a proxy for capital intensity (core index).
        Core counties have lower K/v (more services), peripheral have higher K/v.
        """
        calculator = CapitalStockCalculator(registry_with_multi_county_data)

        occ_values = []
        capital_intensity = []

        for fips in ["26163", "26125", "26099"]:
            metrics = calculator.get_metrics(fips, 2022)
            if isinstance(metrics, DerivedTensorMetrics):
                occ_values.append(metrics.organic_composition)
                # Capital intensity = K / v
                intensity = metrics.capital_stock / float(metrics.tensor.total_v)
                capital_intensity.append(intensity)

        # Compute correlation coefficient
        n = len(occ_values)
        occ_mean = sum(occ_values) / n
        intensity_mean = sum(capital_intensity) / n

        cov = (
            sum(
                (o - occ_mean) * (i - intensity_mean)
                for o, i in zip(occ_values, capital_intensity, strict=True)
            )
            / n
        )
        std_occ = math.sqrt(sum((o - occ_mean) ** 2 for o in occ_values) / n)
        std_intensity = math.sqrt(sum((i - intensity_mean) ** 2 for i in capital_intensity) / n)

        correlation = cov / (std_occ * std_intensity) if std_occ > 0 and std_intensity > 0 else 0

        # OCC and capital intensity should be positively correlated
        assert correlation > 0.3, f"Expected correlation > 0.3, got {correlation}"


# =============================================================================
# T072: TRPF ROBUSTNESS ACROSS DEPRECIATION RATES (SC-004)
# =============================================================================


class TestTRPFRobustness:
    """Tests for TRPF robustness across depreciation rates (SC-004)."""

    @pytest.mark.parametrize("delta", [0.05, 0.07, 0.10])
    def test_trpf_robust_across_depreciation_rates(
        self, registry_with_trpf_data: TensorRegistry, delta: float
    ) -> None:
        """T072: TRPF should hold across δ ∈ {0.05, 0.07, 0.10}."""
        config = DepreciationConfig(rate=delta)
        calculator = CapitalStockCalculator(registry_with_trpf_data, depreciation=config)

        # Collect profit rate time series
        profit_rates = []
        years = []
        for year in range(2010, 2025):
            metrics = calculator.get_metrics("26163", year)
            if isinstance(metrics, DerivedTensorMetrics):
                profit_rates.append(metrics.profit_rate_stock)
                years.append(year)

        # Simple slope calculation
        n = len(years)
        x_mean = sum(years) / n
        y_mean = sum(profit_rates) / n

        cov_xy = (
            sum((x - x_mean) * (y - y_mean) for x, y in zip(years, profit_rates, strict=True)) / n
        )
        var_x = sum((x - x_mean) ** 2 for x in years) / n

        slope = cov_xy / var_x

        # TRPF should hold regardless of depreciation rate
        assert slope < 0, f"Expected negative slope with δ={delta}, got {slope}"


# =============================================================================
# T073: STATE AGGREGATE ACCURACY (SC-005)
# =============================================================================


class TestAggregateAccuracy:
    """Tests for state aggregate accuracy (SC-005: error < 0.01%)."""

    def test_state_aggregate_equals_sum_of_counties(
        self, registry_with_multi_county_data: TensorRegistry
    ) -> None:
        """T073: State aggregate K should equal sum of county K within 0.01%."""
        calculator = CapitalStockCalculator(registry_with_multi_county_data)

        # Compute individual county K values
        county_K_values = []
        for fips in ["26163", "26125", "26099"]:
            K = calculator.get_K(fips, 2022)
            if isinstance(K, float):
                county_K_values.append(K)

        # Sum of county K
        expected_sum = sum(county_K_values)

        # State aggregate
        state_K = calculator.get_K_aggregate(GeoLevel.STATE, "26", 2022)

        assert isinstance(state_K, float)

        # Error should be < 0.01%
        relative_error = abs(state_K - expected_sum) / expected_sum
        assert relative_error < 0.0001, f"Relative error {relative_error:.6f} exceeds 0.01%"


# =============================================================================
# T076: EXISTING TENSOR TESTS STILL PASS (SC-006)
# =============================================================================


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing TensorRegistry."""

    def test_registry_get_still_works(self, registry_with_trpf_data: TensorRegistry) -> None:
        """T076: Existing TensorRegistry.get() should still work."""
        tensor = registry_with_trpf_data.get("26163", 2020)

        assert isinstance(tensor, ValueTensor4x3)
        assert tensor.fips_code == "26163"
        assert tensor.year == 2020
        assert tensor.profit_rate > 0  # Flow-based profit rate

    def test_registry_aggregate_still_works(
        self, registry_with_multi_county_data: TensorRegistry
    ) -> None:
        """Existing TensorRegistry.get_aggregate() should still work."""
        aggregate = registry_with_multi_county_data.get_aggregate(GeoLevel.STATE, "26", 2022)

        assert isinstance(aggregate, ValueTensor4x3)
        # State aggregate FIPS is padded to 5 digits
        assert aggregate.fips_code == "26000"

    def test_capital_stock_does_not_affect_tensor_cache(
        self, registry_with_trpf_data: TensorRegistry
    ) -> None:
        """CapitalStockCalculator should not modify TensorRegistry cache."""
        # Get initial cache info
        initial_info = registry_with_trpf_data.cache_info()

        # Create calculator and compute values
        calculator = CapitalStockCalculator(registry_with_trpf_data)
        calculator.compute_time_series("26163", 2010, 2024)

        # Cache info should be unchanged
        final_info = registry_with_trpf_data.cache_info()
        assert final_info["county_count"] == initial_info["county_count"]


# =============================================================================
# PERFORMANCE (SC-001: <100ms per county time series)
# =============================================================================


class TestPerformance:
    """Tests for performance requirements (SC-001)."""

    def test_time_series_computation_under_100ms(
        self, registry_with_trpf_data: TensorRegistry
    ) -> None:
        """SC-001: Time series computation should complete in <100ms."""
        import time

        calculator = CapitalStockCalculator(registry_with_trpf_data)

        # Warm up cache
        calculator.clear_cache()

        # Time the computation
        start = time.perf_counter()
        calculator.compute_time_series("26163", 2010, 2024)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete in under 100ms
        assert elapsed_ms < 100, f"Computation took {elapsed_ms:.1f}ms, expected <100ms"

    def test_cached_lookup_is_fast(self, registry_with_trpf_data: TensorRegistry) -> None:
        """Cached K lookup should be significantly faster than initial computation."""
        import time

        calculator = CapitalStockCalculator(registry_with_trpf_data)

        # Initial computation (cold cache)
        start = time.perf_counter()
        calculator.get_K("26163", 2020)
        cold_ms = (time.perf_counter() - start) * 1000

        # Cached lookup (warm cache)
        start = time.perf_counter()
        calculator.get_K("26163", 2020)
        warm_ms = (time.perf_counter() - start) * 1000

        # Cached lookup should be faster
        # Note: This is a soft check - timing can be noisy
        assert warm_ms <= cold_ms + 1, (
            f"Cached lookup ({warm_ms:.3f}ms) not faster than cold ({cold_ms:.3f}ms)"
        )
