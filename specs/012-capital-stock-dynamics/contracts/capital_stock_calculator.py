"""Contract: CapitalStockCalculator Protocol.

This module defines the protocol (interface) for capital stock computation.
Implementation should follow this contract.

Feature: 012-capital-stock-dynamics
Phase: 1 - Contracts
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from babylon.economics.tensor import NoDataSentinel, ValueTensor4x3
    from babylon.economics.tensor_registry import GeoLevel


@runtime_checkable
class CapitalStockCalculatorProtocol(Protocol):
    """Protocol for capital stock computation from tensor flows.

    Implementations must provide methods to:
    1. Compute capital stock K for a specific county-year
    2. Compute time series of K for a county
    3. Compute aggregated K for state/nation levels
    4. Produce DerivedTensorMetrics combining K with tensor data

    Thread Safety:
        All methods must be thread-safe for concurrent access.

    Caching:
        Implementations should cache computed K values to avoid
        recomputation. Cache should be invalidated when source
        tensor data changes.
    """

    @property
    def depreciation_rate(self) -> float:
        """Get the depreciation rate δ used for K computation.

        Returns:
            Depreciation rate as a float in range [0.01, 0.20].
        """
        ...

    def get_K(self, fips: str, year: int) -> float | NoDataSentinel:
        """Get capital stock for a specific county-year.

        Computes K using the perpetual inventory method:
            K[t] = K[t-1] × (1 - δ) + total_c[t-1]

        For the initial year, uses steady-state assumption:
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
        ...

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
            start_year: First year to include (default: registry MIN_YEAR).
            end_year: Last year to include (default: registry MAX_YEAR).

        Returns:
            Dictionary mapping year (int) to capital stock K (float).
            Only includes years with available tensor data.

        Example:
            >>> time_series = calculator.compute_time_series("26163", 2010, 2024)
            >>> for year, K in time_series.items():
            ...     print(f"{year}: K = {K:,.0f}")
        """
        ...

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
            When coverage is ≥50% but <100%, the aggregation proceeds
            with a warning logged noting partial coverage.

        Example:
            >>> michigan_K = calculator.get_K_aggregate(GeoLevel.STATE, "26", 2022)
            >>> national_K = calculator.get_K_aggregate(GeoLevel.NATION, "US", 2022)
        """
        ...

    def get_metrics(
        self,
        fips: str,
        year: int,
    ) -> DerivedTensorMetricsProtocol | NoDataSentinel:
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
        ...

    def clear_cache(self) -> None:
        """Clear all cached capital stock values.

        Should be called when underlying tensor data changes.
        """
        ...

    def cache_info(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics:
            - county_count: Number of cached (fips, year) entries
            - time_series_count: Number of cached time series
            - hits: Cache hits
            - misses: Cache misses
        """
        ...


@runtime_checkable
class DerivedTensorMetricsProtocol(Protocol):
    """Protocol for derived tensor metrics container.

    Implementations must be immutable (frozen dataclass or similar).
    """

    @property
    def fips_code(self) -> str:
        """5-digit FIPS county code."""
        ...

    @property
    def year(self) -> int:
        """Calendar year."""
        ...

    @property
    def capital_stock(self) -> float:
        """Capital stock K in labor-hours."""
        ...

    @property
    def profit_rate_stock(self) -> float:
        """Stock-based profit rate r = s / (K + v)."""
        ...

    @property
    def organic_composition(self) -> float:
        """Organic composition of capital OCC = c / v."""
        ...

    @property
    def exploitation_rate(self) -> float:
        """Exploitation rate e = s / v."""
        ...

    @property
    def tensor(self) -> ValueTensor4x3:
        """Source ValueTensor4x3."""
        ...

    @property
    def depreciation_rate(self) -> float:
        """Depreciation rate δ used for K computation."""
        ...

    @property
    def profit_rate_flow(self) -> float:
        """Flow-based profit rate s/(c+v) from underlying tensor."""
        ...

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for analysis/export."""
        ...
