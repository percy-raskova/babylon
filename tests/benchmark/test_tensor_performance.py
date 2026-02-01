"""Performance benchmarks for tensor operations.

Feature: 011-fundamental-tensor-primitive
Implements: T064, T066, T067 from tasks.md

These tests verify performance requirements:
- T064: 100 counties × 10 years < 5 seconds hydration
- T066: get() p95 latency < 1ms
- T067: get_aggregate() cold < 100ms, warm < 1ms
"""

from __future__ import annotations

import statistics
import time
from typing import TYPE_CHECKING

import pytest

from babylon.economics.tensor import DepartmentRow, ValueTensor4x3
from babylon.economics.tensor_registry import GeoLevel, TensorRegistry

if TYPE_CHECKING:
    pass


# =============================================================================
# PERFORMANCE CONSTANTS
# =============================================================================

# T064: Hydration performance
HYDRATION_COUNTIES = 100
HYDRATION_YEARS = 10
HYDRATION_MAX_SECONDS = 5.0

# T066: get() latency
GET_ITERATIONS = 1000
GET_P95_MAX_MS = 1.0

# T067: get_aggregate() latency
AGGREGATE_COLD_MAX_MS = 100.0
AGGREGATE_WARM_MAX_MS = 1.0
AGGREGATE_ITERATIONS = 100


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def populated_registry() -> TensorRegistry:
    """Create a registry pre-populated with test data."""
    reg = TensorRegistry()

    # Generate 100 fake county FIPS codes across multiple states
    states = ["26", "06", "36", "48", "12"]  # MI, CA, NY, TX, FL
    counties_per_state = HYDRATION_COUNTIES // len(states)

    for state in states:
        for i in range(counties_per_state):
            fips = f"{state}{i:03d}"
            for year in range(2015, 2015 + HYDRATION_YEARS):
                reg.put(
                    fips,
                    year,
                    ValueTensor4x3(
                        fips_code=fips,
                        year=year,
                        dept_I=DepartmentRow(c=1000.0 + i * 10, v=500.0 + i * 5, s=250.0 + i * 2.5),
                        dept_IIa=DepartmentRow(c=800.0 + i * 8, v=400.0 + i * 4, s=200.0 + i * 2),
                        dept_IIb=DepartmentRow(c=600.0 + i * 6, v=300.0 + i * 3, s=150.0 + i * 1.5),
                        dept_III=DepartmentRow(c=400.0 + i * 4, v=200.0 + i * 2, s=100.0 + i * 1),
                        naics_granularity=0.9,
                        excluded_wages=5000.0 + i * 50,
                    ),
                )

    return reg


# =============================================================================
# T064: HYDRATION PERFORMANCE
# =============================================================================


@pytest.mark.benchmark
class TestHydrationPerformance:
    """Tests for tensor hydration performance."""

    def test_put_100_counties_10_years_under_5_seconds(self) -> None:
        """Putting 100 counties × 10 years should complete in < 5 seconds."""
        reg = TensorRegistry()

        start = time.perf_counter()

        # Simulate hydration by putting tensors
        for county_idx in range(HYDRATION_COUNTIES):
            fips = f"26{county_idx:03d}"
            for year in range(2015, 2015 + HYDRATION_YEARS):
                reg.put(
                    fips,
                    year,
                    ValueTensor4x3(
                        fips_code=fips,
                        year=year,
                        dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
                        dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
                        dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
                        dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
                        naics_granularity=0.9,
                        excluded_wages=5000.0,
                    ),
                )

        elapsed = time.perf_counter() - start

        # Verify count
        info = reg.cache_info()
        expected_count = HYDRATION_COUNTIES * HYDRATION_YEARS
        assert info["county_count"] == expected_count, (
            f"Expected {expected_count} tensors, got {info['county_count']}"
        )

        # Verify performance
        assert elapsed < HYDRATION_MAX_SECONDS, (
            f"Hydration took {elapsed:.2f}s, expected < {HYDRATION_MAX_SECONDS}s"
        )


# =============================================================================
# T066: GET() LATENCY
# =============================================================================


@pytest.mark.benchmark
class TestGetLatency:
    """Tests for get() operation latency."""

    def test_get_p95_under_1ms(self, populated_registry: TensorRegistry) -> None:
        """get() p95 latency should be < 1ms."""
        # Get a sample FIPS that exists
        fips = "26000"
        year = 2020

        # Warm up
        for _ in range(10):
            populated_registry.get(fips, year)

        # Measure latencies
        latencies_ms: list[float] = []
        for _ in range(GET_ITERATIONS):
            start = time.perf_counter()
            populated_registry.get(fips, year)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)

        # Calculate p95
        latencies_ms.sort()
        p95_idx = int(len(latencies_ms) * 0.95)
        p95_latency = latencies_ms[p95_idx]

        assert p95_latency < GET_P95_MAX_MS, (
            f"get() p95 latency was {p95_latency:.3f}ms, expected < {GET_P95_MAX_MS}ms"
        )

    def test_get_mean_latency_reasonable(self, populated_registry: TensorRegistry) -> None:
        """get() mean latency should be well under 1ms."""
        fips = "26000"
        year = 2020

        latencies_ms: list[float] = []
        for _ in range(GET_ITERATIONS):
            start = time.perf_counter()
            populated_registry.get(fips, year)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)

        mean_latency = statistics.mean(latencies_ms)

        # Mean should be much lower than p95 requirement
        assert mean_latency < GET_P95_MAX_MS / 2, (
            f"get() mean latency was {mean_latency:.3f}ms, expected < {GET_P95_MAX_MS / 2}ms"
        )


# =============================================================================
# T067: GET_AGGREGATE() LATENCY
# =============================================================================


@pytest.mark.benchmark
class TestAggregateLatency:
    """Tests for get_aggregate() operation latency."""

    def test_get_aggregate_cold_under_100ms(self, populated_registry: TensorRegistry) -> None:
        """get_aggregate() cold (first call) should be < 100ms."""
        # Clear any cached aggregates
        populated_registry.clear()

        # Re-populate (we need data to aggregate)
        for i in range(20):  # 20 counties in Michigan
            fips = f"26{i:03d}"
            populated_registry.put(
                fips,
                2022,
                ValueTensor4x3(
                    fips_code=fips,
                    year=2022,
                    dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
                    dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
                    dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
                    dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
                    naics_granularity=0.9,
                    excluded_wages=5000.0,
                ),
            )

        # Cold call (not in cache)
        start = time.perf_counter()
        populated_registry.get_aggregate(GeoLevel.STATE, "26", 2022)
        cold_latency_ms = (time.perf_counter() - start) * 1000

        assert cold_latency_ms < AGGREGATE_COLD_MAX_MS, (
            f"get_aggregate() cold latency was {cold_latency_ms:.3f}ms, "
            f"expected < {AGGREGATE_COLD_MAX_MS}ms"
        )

    def test_get_aggregate_warm_under_1ms(self, populated_registry: TensorRegistry) -> None:
        """get_aggregate() warm (cached) should be < 1ms."""
        # Ensure we have Michigan counties
        for i in range(20):
            fips = f"26{i:03d}"
            populated_registry.put(
                fips,
                2022,
                ValueTensor4x3(
                    fips_code=fips,
                    year=2022,
                    dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
                    dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
                    dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
                    dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
                    naics_granularity=0.9,
                    excluded_wages=5000.0,
                ),
            )

        # First call to warm the cache
        populated_registry.get_aggregate(GeoLevel.STATE, "26", 2022)

        # Warm calls
        latencies_ms: list[float] = []
        for _ in range(AGGREGATE_ITERATIONS):
            start = time.perf_counter()
            populated_registry.get_aggregate(GeoLevel.STATE, "26", 2022)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)

        # Check p95 of warm latencies
        latencies_ms.sort()
        p95_idx = int(len(latencies_ms) * 0.95)
        p95_latency = latencies_ms[p95_idx]

        assert p95_latency < AGGREGATE_WARM_MAX_MS, (
            f"get_aggregate() warm p95 latency was {p95_latency:.3f}ms, "
            f"expected < {AGGREGATE_WARM_MAX_MS}ms"
        )

    def test_nation_aggregate_scales_reasonably(self, populated_registry: TensorRegistry) -> None:
        """Nation aggregate with many counties should complete in reasonable time."""
        # First call to cache (may be slow)
        start = time.perf_counter()
        populated_registry.get_aggregate(GeoLevel.NATION, "US", 2020)
        cold_latency_ms = (time.perf_counter() - start) * 1000

        # Should complete in < 500ms even for nation aggregate
        assert cold_latency_ms < 500, (
            f"Nation aggregate cold latency was {cold_latency_ms:.3f}ms, expected < 500ms"
        )
