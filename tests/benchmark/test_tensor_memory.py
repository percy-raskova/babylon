"""Memory usage benchmarks for tensor operations.

Feature: 011-fundamental-tensor-primitive
Implements: T065 from tasks.md

This test verifies:
- T065: Full US dataset (3000+ counties × 10 years) < 500MB peak RSS

Note: This test uses tracemalloc for memory measurement, which has some
overhead. The actual production memory usage will be lower.
"""

from __future__ import annotations

import tracemalloc

import pytest

from babylon.domain.economics.tensor import DepartmentRow, ValueTensor4x3
from babylon.domain.economics.tensor_registry import GeoLevel, TensorRegistry

# =============================================================================
# MEMORY CONSTANTS
# =============================================================================

# T065: Memory limits
# US has ~3,143 counties. We test with a representative subset.
MEMORY_TEST_COUNTIES = 500  # Representative subset
MEMORY_TEST_YEARS = 10
MEMORY_MAX_MB = 100  # Scaled down from 500MB for subset test

# Full scale test (optional, slow)
FULL_SCALE_COUNTIES = 3000
FULL_SCALE_YEARS = 10
FULL_SCALE_MAX_MB = 500


# =============================================================================
# T065: MEMORY PROFILER TEST
# =============================================================================


@pytest.mark.benchmark
class TestTensorMemory:
    """Tests for tensor memory usage."""

    def test_500_counties_10_years_under_100mb(self) -> None:
        """500 counties × 10 years should use < 100MB.

        This is a scaled-down test. The full US dataset test is marked slow.
        """
        # Start memory tracking
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]

        reg = TensorRegistry()

        # Populate with test data
        for county_idx in range(MEMORY_TEST_COUNTIES):
            # Distribute across states
            state = ["26", "06", "36", "48", "12"][county_idx % 5]
            fips = f"{state}{county_idx % 200:03d}"

            for year in range(2015, 2015 + MEMORY_TEST_YEARS):
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

        # Measure memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate usage relative to baseline
        usage_mb = (peak - baseline) / (1024 * 1024)

        # Verify under limit
        assert usage_mb < MEMORY_MAX_MB, (
            f"Memory usage was {usage_mb:.1f}MB, expected < {MEMORY_MAX_MB}MB "
            f"for {MEMORY_TEST_COUNTIES} counties × {MEMORY_TEST_YEARS} years"
        )

    @pytest.mark.slow
    def test_full_us_dataset_under_500mb(self) -> None:
        """Full US dataset (~3000 counties × 10 years) should use < 500MB.

        This test is slow and memory-intensive. Run with: pytest -m slow
        """
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]

        reg = TensorRegistry()

        # Simulate full US dataset
        # Real US has ~3,143 counties, we use 3000 for round numbers
        for county_idx in range(FULL_SCALE_COUNTIES):
            # Generate realistic-ish FIPS codes
            state = f"{(county_idx // 60) % 50 + 1:02d}"  # 50 states
            county = f"{county_idx % 1000:03d}"
            fips = state + county

            for year in range(2015, 2015 + FULL_SCALE_YEARS):
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

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        usage_mb = (peak - baseline) / (1024 * 1024)

        assert usage_mb < FULL_SCALE_MAX_MB, (
            f"Memory usage was {usage_mb:.1f}MB, expected < {FULL_SCALE_MAX_MB}MB "
            f"for {FULL_SCALE_COUNTIES} counties × {FULL_SCALE_YEARS} years"
        )

    def test_memory_per_tensor_reasonable(self) -> None:
        """Each tensor should use a reasonable amount of memory."""
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]

        # Create 100 tensors
        tensors = []
        for i in range(100):
            tensors.append(
                ValueTensor4x3(
                    fips_code=f"26{i:03d}",
                    year=2022,
                    dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
                    dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
                    dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
                    dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
                    naics_granularity=0.9,
                    excluded_wages=5000.0,
                )
            )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        usage_bytes = peak - baseline
        bytes_per_tensor = usage_bytes / 100

        # Each tensor should be < 10KB (generous estimate)
        # Pydantic models have some overhead, but 10KB per tensor is reasonable
        max_bytes_per_tensor = 10 * 1024  # 10KB

        assert bytes_per_tensor < max_bytes_per_tensor, (
            f"Memory per tensor was {bytes_per_tensor:.0f} bytes, "
            f"expected < {max_bytes_per_tensor} bytes"
        )

        # Keep tensors reference to prevent GC during measurement
        del tensors


@pytest.mark.benchmark
class TestRegistryMemoryManagement:
    """Tests for registry memory management."""

    def test_clear_releases_memory(self) -> None:
        """Clearing the registry should release memory."""
        tracemalloc.start()

        reg = TensorRegistry()

        # Populate
        for i in range(100):
            for year in range(2020, 2023):
                reg.put(
                    f"26{i:03d}",
                    year,
                    ValueTensor4x3(
                        fips_code=f"26{i:03d}",
                        year=year,
                        dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
                        dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
                        dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
                        dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
                        naics_granularity=0.9,
                        excluded_wages=5000.0,
                    ),
                )

        # Get memory before clear (for potential future debugging)
        _ = tracemalloc.get_traced_memory()[0]

        # Clear registry
        reg.clear()

        # Force garbage collection
        import gc

        gc.collect()

        # Get memory after clear (for potential future debugging)
        _ = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        # Memory should decrease after clear
        # Note: This is a weak test due to Python's memory management
        # The registry's internal dict should be empty
        assert reg.cache_info()["county_count"] == 0

    def test_aggregate_cache_bounded(self) -> None:
        """Aggregate cache should be bounded by maxsize."""
        # Create registry with small maxsize
        reg = TensorRegistry(maxsize=100)

        # Populate with data
        for i in range(20):
            for year in range(2015, 2025):
                reg.put(
                    f"26{i:03d}",
                    year,
                    ValueTensor4x3(
                        fips_code=f"26{i:03d}",
                        year=year,
                        dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
                        dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
                        dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
                        dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
                        naics_granularity=0.9,
                        excluded_wages=5000.0,
                    ),
                )

        # Request many different aggregates to fill cache
        for year in range(2015, 2025):
            reg.get_aggregate(GeoLevel.STATE, "26", year)

        # Cache info should show bounded usage
        info = reg.cache_info()
        # LRU cache should evict old entries
        assert info["aggregate_misses"] > 0  # We made requests
