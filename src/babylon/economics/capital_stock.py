"""Capital stock computation from tensor flow data.

This module provides the CapitalStockCalculator service for computing capital
stock (K) from constant capital flows (c) using the perpetual inventory method.

Theoretical Foundation:
    Capital stock evolves according to TVT Axiom A3 (Stock-Flow Consistency)::

        K[fips, t+1] = K[fips, t] × (1 - δ) + Σ_μ c^μ[fips, t]

    Where:
        K = Capital stock (accumulated constant capital in labor-hours)
        δ = Depreciation rate (annual fraction consumed)
        Σ_μ c^μ = Total constant capital flow (total_c from ValueTensor4x3)

    Initial capital stock uses steady-state assumption (TVT Section 5.2)::

        K_0 = total_c_0 / δ

    The stock-based profit rate (TVT Section 3.6)::

        r = Σ_μ s^μ / (K + Σ_μ v^μ)

    This differs from the flow-based rate s/(c+v) in ValueTensor4x3.

Example:
    >>> from babylon.economics.tensor_registry import TensorRegistry
    >>> from babylon.economics.capital_stock import CapitalStockCalculator
    >>>
    >>> registry = TensorRegistry()
    >>> # ... hydrate registry ...
    >>> calculator = CapitalStockCalculator(registry)
    >>> K = calculator.get_K("26163", 2022)
    >>> if K:
    ...     print(f"Capital stock: {K:,.0f} labor-hours")

See Also:
    :class:`babylon.economics.depreciation.DepreciationConfig`: Depreciation configuration.
    :class:`babylon.economics.derived_metrics.DerivedTensorMetrics`: Metrics container.
    :class:`babylon.economics.tensor_registry.TensorRegistry`: Tensor data source.
    TVT Section 3.6: Stock-based profit rate formula.
    TVT Section 5.2: Capital stock evolution formula.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Final

from babylon.economics.depreciation import DepreciationConfig
from babylon.economics.tensor import NoDataSentinel, ValueTensor4x3

if TYPE_CHECKING:
    from babylon.economics.derived_metrics import DerivedTensorMetrics
    from babylon.economics.tensor_registry import GeoLevel, TensorRegistry

__all__ = [
    "CapitalStockCalculator",
]

logger = logging.getLogger(__name__)


class CapitalStockCalculator:
    """Computes capital stock (K) from constant capital flows (c).

    Uses the perpetual inventory method with TSSI historical cost valuation::

        K[t+1] = K[t] × (1 - δ) + Σ_μ c^μ[t]

    Initial capital stock assumes steady state::

        K_0 = c_0 / δ

    The calculator caches computed K values to avoid recomputation.
    Thread-safe for concurrent access.

    Args:
        registry: TensorRegistry providing access to ValueTensor4x3 data.
        depreciation: Depreciation configuration. Defaults to δ = 0.07.

    Example:
        >>> registry = TensorRegistry()
        >>> # ... hydrate registry with data ...
        >>> calculator = CapitalStockCalculator(registry)
        >>> K = calculator.get_K("26163", 2022)
        >>> if K:
        ...     print(f"Capital stock: {K:,.0f} labor-hours")
    """

    # Valid year range matches TensorRegistry
    MIN_YEAR: Final[int] = 2010
    MAX_YEAR: Final[int] = 2025

    def __init__(
        self,
        registry: TensorRegistry,
        depreciation: DepreciationConfig | None = None,
    ) -> None:
        """Initialize the capital stock calculator.

        Args:
            registry: TensorRegistry providing access to ValueTensor4x3 data.
            depreciation: Depreciation configuration. Defaults to δ = 0.07.
        """
        self._registry: Final[TensorRegistry] = registry
        self._depreciation: Final[DepreciationConfig] = depreciation or DepreciationConfig.default()

        # Primary cache: (fips, year) -> K value
        self._cache: dict[tuple[str, int], float] = {}

        # Time series cache: fips -> dict[year, K]
        self._time_series_cache: dict[str, dict[int, float]] = {}

        # Cache statistics
        self._hits: int = 0
        self._misses: int = 0

        # Thread safety
        self._lock = threading.RLock()

        logger.debug(
            "CapitalStockCalculator initialized with δ = %.4f",
            self._depreciation.rate,
        )

    @property
    def depreciation_rate(self) -> float:
        """Get the depreciation rate δ.

        Returns:
            Depreciation rate as a float in range [0.01, 0.20].
        """
        return self._depreciation.rate

    def get_K(self, fips: str, year: int) -> float | NoDataSentinel:
        """Get capital stock for a specific county-year.

        Computes K using the perpetual inventory method::

            K[t] = K[t-1] × (1 - δ) + total_c[t-1]

        For the initial year, uses steady-state assumption::

            K_0 = total_c_0 / δ

        Args:
            fips: 5-digit FIPS county code (e.g., "26163").
            year: Calendar year (e.g., 2022).

        Returns:
            Capital stock K in labor-hours (float >= 0),
            or NoDataSentinel if data is unavailable.

        Example:
            >>> K = calculator.get_K("26163", 2022)
            >>> if K:
            ...     print(f"Capital stock: {K:,.0f} labor-hours")
            ... else:
            ...     print(f"No data: {K.reason}")
        """
        # Check year boundaries
        if year < self.MIN_YEAR or year > self.MAX_YEAR:
            return NoDataSentinel(
                fips,
                year,
                f"Year {year} outside available data range ({self.MIN_YEAR}-{self.MAX_YEAR})",
            )

        # Check cache first
        with self._lock:
            cache_key = (fips, year)
            if cache_key in self._cache:
                self._hits += 1
                logger.debug("get_K(%s, %d): Cache hit", fips, year)
                return self._cache[cache_key]

        # Not in cache - compute time series
        self._misses += 1
        logger.debug("get_K(%s, %d): Cache miss, computing time series", fips, year)

        time_series = self.compute_time_series(fips)

        if year not in time_series:
            return NoDataSentinel(
                fips,
                year,
                f"No tensor data available for FIPS {fips} in year {year}",
            )

        return time_series[year]

    def compute_time_series(
        self,
        fips: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[int, float]:
        """Compute capital stock for all available years in range.

        Uses perpetual inventory method starting from first available year.
        Missing years within the range are skipped (not interpolated).

        Args:
            fips: 5-digit FIPS county code.
            start_year: First year to include. Defaults to MIN_YEAR.
            end_year: Last year to include. Defaults to MAX_YEAR.

        Returns:
            Dictionary mapping year (int) to capital stock K (float).
            Only includes years with available tensor data.

        Example:
            >>> time_series = calculator.compute_time_series("26163", 2010, 2024)
            >>> for year, K in time_series.items():
            ...     print(f"{year}: K = {K:,.0f}")
        """
        start = start_year if start_year is not None else self.MIN_YEAR
        end = end_year if end_year is not None else self.MAX_YEAR

        # Check if we have a cached time series
        with self._lock:
            if fips in self._time_series_cache:
                cached = self._time_series_cache[fips]
                # Return filtered subset if cached
                return {y: k for y, k in cached.items() if start <= y <= end}

        # Build time series from scratch
        results: dict[int, float] = {}
        K_prev: float | None = None

        for year in range(start, end + 1):
            tensor = self._registry.get(fips, year)

            if not tensor:  # NoDataSentinel
                if K_prev is not None:
                    logger.warning(
                        "Missing tensor data for %s/%d, skipping year",
                        fips,
                        year,
                    )
                continue

            # Must be ValueTensor4x3 at this point
            assert isinstance(tensor, ValueTensor4x3)

            if K_prev is None:
                # Initial year: steady-state assumption
                K_0 = self._depreciation.steady_state_K(float(tensor.total_c))
                results[year] = K_0
                K_prev = K_0
                logger.debug(
                    "compute_time_series(%s): K_0[%d] = %.2f (steady state)",
                    fips,
                    year,
                    K_0,
                )
            else:
                # Perpetual inventory method
                # Note: K[t] = K[t-1] × (1 - δ) + total_c[t-1]
                # The investment is from the PREVIOUS period
                K_new = self._depreciation.next_K(K_prev, float(tensor.total_c))
                results[year] = K_new
                K_prev = K_new
                logger.debug(
                    "compute_time_series(%s): K[%d] = %.2f",
                    fips,
                    year,
                    K_new,
                )

        # Cache the time series and individual values
        with self._lock:
            self._time_series_cache[fips] = results.copy()
            for year, K in results.items():
                self._cache[(fips, year)] = K

        return results

    def get_K_aggregate(
        self,
        level: GeoLevel,
        code: str,
        year: int,
    ) -> float | NoDataSentinel:
        """Get aggregated capital stock for state or nation.

        Aggregates are computed as the sum of constituent county K values.
        Requires at least 50% of counties to have valid K data.

        Args:
            level: Aggregation level (STATE or NATION).
            code: Geographic code:
                - STATE: 2-digit state FIPS (e.g., "26" for Michigan)
                - NATION: "US" for national aggregate
            year: Calendar year.

        Returns:
            Aggregated capital stock (sum of county K values),
            or NoDataSentinel with reason "Insufficient county coverage (X%)"
            if less than 50% of counties have valid K data.

        Note:
            When coverage is >= 50% but < 100%, the aggregation proceeds
            with a warning logged noting partial coverage.

        Example:
            >>> michigan_K = calculator.get_K_aggregate(GeoLevel.STATE, "26", 2022)
            >>> national_K = calculator.get_K_aggregate(GeoLevel.NATION, "US", 2022)
        """
        # Import locally to avoid circular dependency
        from babylon.economics.tensor_registry import GeoLevel

        # Year boundary check
        if year < self.MIN_YEAR or year > self.MAX_YEAR:
            return NoDataSentinel(
                code,
                year,
                f"Year {year} outside available data range ({self.MIN_YEAR}-{self.MAX_YEAR})",
            )

        # Get all counties for this level
        if level == GeoLevel.COUNTY:
            # Single county - just return get_K
            return self.get_K(code, year)

        # Get list of county FIPS codes
        county_fips = self._get_counties_for_level(level, code)

        if not county_fips:
            return NoDataSentinel(
                code,
                year,
                f"No counties found for {level.value} {code}",
            )

        # Compute K for each county
        valid_K_values: list[float] = []
        for fips in county_fips:
            K = self.get_K(fips, year)
            if isinstance(K, float):
                valid_K_values.append(K)

        # Check coverage threshold (50%)
        coverage = len(valid_K_values) / len(county_fips)
        coverage_pct = coverage * 100

        if coverage < 0.5:
            return NoDataSentinel(
                code,
                year,
                f"Insufficient county coverage ({coverage_pct:.0f}%)",
            )

        if coverage < 1.0:
            logger.warning(
                "get_K_aggregate(%s, %s, %d): Partial coverage (%.0f%%), returning sum of available counties",
                level.value,
                code,
                year,
                coverage_pct,
            )

        return sum(valid_K_values)

    def _get_counties_for_level(self, level: GeoLevel, code: str) -> list[str]:
        """Get list of county FIPS codes for a geographic level.

        Args:
            level: Aggregation level (STATE or NATION).
            code: Geographic code.

        Returns:
            List of 5-digit county FIPS codes.
        """
        from babylon.economics.tensor_registry import GeoLevel

        # Get all counties from registry cache
        cache_info = self._registry.cache_info()
        if cache_info["county_count"] == 0:
            return []

        # Use cached FIPS codes to find counties
        # This relies on counties being previously computed via get_K or compute_time_series
        with self._lock:
            cached_fips = {key[0] for key in self._cache}

        # Also need to check registry directly
        # For now, use a simple approach: check for counties by state prefix
        if level == GeoLevel.STATE:
            # Filter by state prefix
            return [fips for fips in cached_fips if fips.startswith(code)]
        elif level == GeoLevel.NATION:
            return list(cached_fips)
        else:
            return []

    def get_metrics(
        self,
        fips: str,
        year: int,
    ) -> DerivedTensorMetrics | NoDataSentinel:
        """Get derived metrics combining tensor and capital stock.

        Computes the stock-based profit rate and packages all derived
        values into a DerivedTensorMetrics container.

        Args:
            fips: 5-digit FIPS county code.
            year: Calendar year.

        Returns:
            DerivedTensorMetrics with K, profit_rate_stock, OCC, e,
            or NoDataSentinel if data is unavailable.

        Example:
            >>> metrics = calculator.get_metrics("26163", 2022)
            >>> if metrics:
            ...     print(f"r_stock = {metrics.profit_rate_stock:.4f}")
        """
        # Import here to avoid circular dependency
        from babylon.economics.derived_metrics import DerivedTensorMetrics

        # Get tensor
        tensor_result = self._registry.get(fips, year)
        if not tensor_result:
            return NoDataSentinel(
                fips,
                year,
                f"No tensor data available for FIPS {fips} in year {year}",
            )

        # Type narrowing: at this point tensor_result is ValueTensor4x3
        assert isinstance(tensor_result, ValueTensor4x3)
        tensor: ValueTensor4x3 = tensor_result

        # Get capital stock
        K = self.get_K(fips, year)
        if not isinstance(K, float):
            return K  # Return the NoDataSentinel

        # Compute stock-based profit rate: r = s / (K + v)
        denominator = K + float(tensor.total_v)
        if denominator == 0.0:
            profit_rate_stock = float("inf")
        else:
            profit_rate_stock = float(tensor.total_s) / denominator

        # OCC and exploitation rate are on tensor, but compute here for explicitness
        occ = tensor.organic_composition
        exploitation_rate = tensor.exploitation_rate

        return DerivedTensorMetrics(
            fips_code=fips,
            year=year,
            capital_stock=K,
            profit_rate_stock=profit_rate_stock,
            organic_composition=occ,
            exploitation_rate=exploitation_rate,
            tensor=tensor,
            depreciation_rate=self._depreciation.rate,
        )

    def clear_cache(self) -> None:
        """Clear all cached capital stock values.

        Should be called when underlying tensor data changes.
        """
        with self._lock:
            self._cache.clear()
            self._time_series_cache.clear()
            self._hits = 0
            self._misses = 0
        logger.info("CapitalStockCalculator cache cleared")

    def cache_info(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics:
            - county_count: Number of cached (fips, year) entries
            - time_series_count: Number of cached time series
            - hits: Cache hits
            - misses: Cache misses
        """
        with self._lock:
            return {
                "county_count": len(self._cache),
                "time_series_count": len(self._time_series_cache),
                "hits": self._hits,
                "misses": self._misses,
            }
